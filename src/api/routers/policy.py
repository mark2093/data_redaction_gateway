"""
Policy management API router.
"""
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status

from ...security import verify_api_key, sanitize_log
from ...policy import get_policy_loader

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/policy", tags=["Policy"])


@router.get("/version")
async def get_policy_version(api_key: str = Depends(verify_api_key)):
    """Get current policy version."""
    policy_loader = get_policy_loader()
    
    return {
        'version': policy_loader.get_policy_version(),
        'loaded_at': datetime.utcnow().isoformat(),  # Will be actual load time in final version
        'rule_count': len(policy_loader.get_rules())
    }


@router.post("/reload")
async def reload_policy(api_key: str = Depends(verify_api_key)):
    """Reload policy from YAML file."""
    try:
        policy_loader = get_policy_loader()
        policy = policy_loader.reload_policy()
        
        return {
            'status': 'success',
            'version': policy.version,
            'rule_count': len(policy.rules),
            'reloaded_at': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Policy reload error: {sanitize_log(str(e))}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload policy: {str(e)}"
        )


@router.get("/validate")
async def validate_policy(api_key: str = Depends(verify_api_key)):
    """Validate current policy configuration."""
    from ...policy.validator import PolicyValidator
    
    policy_loader = get_policy_loader()
    policy = policy_loader.get_policy()
    validator = PolicyValidator(policy)
    validation = validator.validate_policy()
    
    return validation


__all__ = ["router"]