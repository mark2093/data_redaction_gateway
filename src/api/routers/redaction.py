"""
Redaction API router.
"""
import time
import logging
import json
from typing import List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status, Request

from ...core.models.api import RedactionRequest, RedactionResponse, DryRunResponse
from ...engines.base import RedactionEngine
from ...policy import get_policy_loader
from ...security import verify_api_key, sanitize_log
from ...observability import MetricsCollector
from ...judge import get_llm_judge
from ...middleware.content import get_processed_body

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/redact", tags=["Redaction"])

# Shared metrics instance (same as metrics router)
from ...observability.metrics import get_metrics_collector
_metrics = get_metrics_collector()



@router.post("/", response_model=RedactionResponse)
async def redact_data(
    request: RedactionRequest,
    fastapi_request: Request,
    api_key: str = Depends(verify_api_key)
):
    """
    Redact sensitive PII/PCI data from input.
    
    This endpoint processes incoming data and redacts sensitive information
    according to configured policies. Approximately 10-20% of requests are
    sampled for LLM-based validation to ensure redaction quality.
    
    Supports automatic decompression of gzip/deflate content and base64 decoding.
    """
    start_time = time.time()
    
    try:
        # Check if we have processed body from content middleware
        processed_body = get_processed_body(fastapi_request)
        if processed_body:
            try:
                # Try to parse the processed body as JSON and update request data
                processed_data = json.loads(processed_body.decode('utf-8'))
                if isinstance(processed_data, dict) and 'data' in processed_data:
                    request.data = processed_data['data']
                    logger.debug("Using decompressed/decoded request body")
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.warning(f"Could not parse processed body as JSON: {e}")
                # Continue with original request data
        # Get policy and rules
        policy_loader = get_policy_loader()
        rules = policy_loader.get_rules()
        
        # Create redaction engine
        engine = RedactionEngine(rules)
        
        # Store original data for judge (if sampled)
        original_data = request.data
        
        # Perform redaction
        redacted_data = engine.redact(request.data)
        redaction_meta = engine.get_redaction_meta() if request.include_meta else None
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000
        
        # Update metrics using shared instance
        _metrics.record_request(processing_time)
        _metrics.record_redactions(len(redaction_meta) if redaction_meta else 0)
        
        # LLM-as-Judge validation (sampled)
        judge_result = None
        llm_judge = get_llm_judge()
        
        if llm_judge.should_sample() and redaction_meta:
            try:
                judge_result = await llm_judge.validate_redaction(
                    original_data=original_data,
                    redacted_data=redacted_data,
                    redaction_meta=redaction_meta
                )
                
                # Record judge call in metrics
                if judge_result is None:
                    _metrics.record_judge_call(fallback=True)
                    logger.info("LLM judge validation fell back to rules-only mode")
                else:
                    _metrics.record_judge_call(fallback=False)
                    logger.info(
                        f"LLM judge validation: coverage={judge_result.coverage_complete}, "
                        f"confidence={judge_result.confidence}%"
                    )
                    
            except Exception as judge_error:
                # Gracefully handle judge errors
                logger.error(f"LLM judge error: {judge_error}", exc_info=True)
                _metrics.record_judge_call(fallback=True)
                judge_result = None
        
        # Build response
        response = RedactionResponse(
            redacted_data=redacted_data,
            redaction_meta=redaction_meta,
            policy_version=policy_loader.get_policy_version(),
            processing_time_ms=processing_time,
            judge_result=judge_result
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Redaction error: {sanitize_log(str(e))}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Redaction processing failed"
        )


@router.post("/dry-run", response_model=DryRunResponse)
async def dry_run_redaction(
    request: RedactionRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Perform dry-run redaction showing before/after comparison.
    
    This endpoint shows what would be redacted without actually applying the changes.
    Useful for testing and validation.
    """
    try:
        # Get policy and rules
        policy_loader = get_policy_loader()
        rules = policy_loader.get_rules()
        
        # Create redaction engine
        engine = RedactionEngine(rules)
        
        # Perform redaction
        redacted_data = engine.redact(request.data)
        redaction_meta = engine.get_redaction_meta()
        
        # Calculate diff
        diff = {
            'redaction_count': len(redaction_meta),
            'fields_affected': list(set([meta.field for meta in redaction_meta])),
            'rules_triggered': list(set([meta.rule for meta in redaction_meta]))
        }
        
        # Build response
        response = DryRunResponse(
            original_data=request.data,
            redacted_data=redacted_data,
            diff=diff,
            redaction_meta=redaction_meta,
            policy_version=policy_loader.get_policy_version()
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Dry-run error: {sanitize_log(str(e))}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Dry-run processing failed"
        )


@router.post("/batch")
async def redact_batch(
    requests: List[RedactionRequest],
    api_key: str = Depends(verify_api_key)
):
    """
    Batch redaction endpoint for processing multiple items.
    
    Processes multiple redaction requests in a single API call.
    Includes LLM Judge validation with batch-aware sampling.
    """
    start_time = time.time()
    
    try:
        # Get policy and rules
        policy_loader = get_policy_loader()
        rules = policy_loader.get_rules()
        
        # Create redaction engine
        engine = RedactionEngine(rules)
        
        # Get LLM Judge for batch validation
        llm_judge = get_llm_judge()
        
        # Process each request
        results = []
        total_redactions = 0
        judge_validations = []
        items_validated = 0
        
        for idx, req in enumerate(requests):
            # Store original data for judge validation
            original_data = req.data
            
            # Perform redaction
            redacted_data = engine.redact(req.data)
            redaction_meta = engine.get_redaction_meta() if req.include_meta else None
            
            # LLM Judge validation (batch-aware sampling)
            judge_result = None
            should_validate = False
            
            # Batch sampling strategy:
            # 1. Always validate at least 1 item per batch (first item if small batch)
            # 2. Apply normal sampling rate for larger batches
            # 3. Ensure minimum coverage for quality assurance
            if redaction_meta:
                if len(requests) <= 5:
                    # Small batch: validate first item
                    should_validate = (idx == 0)
                else:
                    # Large batch: use sampling with minimum guarantee
                    should_validate = llm_judge.should_sample() or (idx == 0 and items_validated == 0)
            
            if should_validate:
                try:
                    judge_result = await llm_judge.validate_redaction(
                        original_data=original_data,
                        redacted_data=redacted_data,
                        redaction_meta=redaction_meta
                    )
                    
                    if judge_result is None:
                        _metrics.record_judge_call(fallback=True)
                        logger.info(f"Batch item {idx}: LLM judge validation fell back to rules-only mode")
                    else:
                        _metrics.record_judge_call(fallback=False)
                        items_validated += 1
                        judge_validations.append({
                            'item_index': idx,
                            'coverage_complete': judge_result.coverage_complete,
                            'over_redacted': judge_result.over_redacted,
                            'under_redacted': judge_result.under_redacted,
                            'confidence': judge_result.confidence,
                            'suggestions': judge_result.suggestions
                        })
                        logger.info(
                            f"Batch item {idx}: LLM judge validation - "
                            f"coverage={judge_result.coverage_complete}, confidence={judge_result.confidence}%"
                        )
                        
                except Exception as judge_error:
                    logger.error(f"Batch item {idx}: LLM judge error: {judge_error}", exc_info=True)
                    _metrics.record_judge_call(fallback=True)
                    judge_result = None
            
            results.append({
                'redacted_data': redacted_data,
                'redaction_meta': redaction_meta,
                'judge_result': judge_result
            })
            
            total_redactions += len(redaction_meta) if redaction_meta else 0
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000
        
        # Update metrics using shared instance
        _metrics.record_request(processing_time)
        _metrics.record_redactions(total_redactions)
        
        # Calculate batch validation summary
        validation_summary = None
        if judge_validations:
            avg_confidence = sum(v['confidence'] for v in judge_validations) / len(judge_validations)
            all_complete = all(v['coverage_complete'] for v in judge_validations)
            any_over_redacted = any(v.get('over_redacted', False) for v in judge_validations)
            any_under_redacted = any(v.get('under_redacted', False) for v in judge_validations)
            total_suggestions = sum(len(v.get('suggestions', [])) for v in judge_validations)
            
            validation_summary = {
                'items_validated': items_validated,
                'validation_rate': round((items_validated / len(requests)) * 100, 2),
                'average_confidence': round(avg_confidence, 2),
                'all_coverage_complete': all_complete,
                'any_over_redacted': any_over_redacted,
                'any_under_redacted': any_under_redacted,
                'total_suggestions': total_suggestions,
                'validations': judge_validations
            }
        
        return {
            'results': results,
            'total_processed': len(requests),
            'total_redactions': total_redactions,
            'policy_version': policy_loader.get_policy_version(),
            'processing_time_ms': processing_time,
            'validation_summary': validation_summary
        }
        
    except Exception as e:
        logger.error(f"Batch redaction error: {sanitize_log(str(e))}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch redaction processing failed"
        )


__all__ = ["router"]