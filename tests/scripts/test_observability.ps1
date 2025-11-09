# Enhanced Observability Test Script

Write-Host "Enhanced Observability & Monitoring Test Suite" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green

$headers = @{
    "X-API-Key" = "test-api-key-67890"
    "Content-Type" = "application/json"
}

Write-Host ""
Write-Host "Test 1: Health Check Endpoints" -ForegroundColor Cyan

# Basic health
try {
    Write-Host "  Testing /health (basic)..."
    $health = Invoke-WebRequest -Uri "http://localhost:8000/health" -Method GET -UseBasicParsing
    $healthData = $health.Content | ConvertFrom-Json
    Write-Host "  Status: $($healthData.status)" -ForegroundColor Green
    Write-Host "  Version: $($healthData.version)"
    Write-Host "  Uptime: $($healthData.uptime_seconds) seconds"
} catch {
    Write-Host "  Basic health check failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Detailed health
try {
    Write-Host ""
    Write-Host "  Testing /health/detailed..."
    $detailedHealth = Invoke-WebRequest -Uri "http://localhost:8000/health/detailed" -Method GET -UseBasicParsing
    $healthDetail = $detailedHealth.Content | ConvertFrom-Json
    Write-Host "  Overall Status: $($healthDetail.status)" -ForegroundColor $(if ($healthDetail.status -eq "healthy") { "Green" } else { "Yellow" })
    Write-Host "  Requests/sec: $($healthDetail.performance.requests_per_second)"
    Write-Host "  Avg Latency: $($healthDetail.performance.avg_latency_ms)ms"
    Write-Host "  P95 Latency: $($healthDetail.performance.p95_latency_ms)ms"
    Write-Host "  Error Rate: $($healthDetail.performance.error_rate)%"
} catch {
    Write-Host "  Detailed health check failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Liveness probe
try {
    Write-Host ""
    Write-Host "  Testing /health/live (Kubernetes liveness)..."
    $live = Invoke-WebRequest -Uri "http://localhost:8000/health/live" -Method GET -UseBasicParsing
    Write-Host "  Liveness: PASS" -ForegroundColor Green
} catch {
    Write-Host "  Liveness probe failed" -ForegroundColor Red
}

# Readiness probe
try {
    Write-Host "  Testing /health/ready (Kubernetes readiness)..."
    $ready = Invoke-WebRequest -Uri "http://localhost:8000/health/ready" -Method GET -UseBasicParsing
    $readyData = $ready.Content | ConvertFrom-Json
    Write-Host "  Readiness: $($readyData.status)" -ForegroundColor Green
    Write-Host "  Rules loaded: $($readyData.rules_loaded)"
} catch {
    Write-Host "  Readiness probe failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Test 2: Generate Test Traffic" -ForegroundColor Cyan

$testRequests = @(
    '{"data":"John Doe SSN 123-45-6789 email john@example.com","include_meta":true}',
    '{"data":"Credit card 4532-1234-5678-9012 phone (555) 123-4567","include_meta":true}',
    '{"data":"IBAN GB82WEST12345698765432 routing 021000021","include_meta":true}'
)

Write-Host "  Sending test requests to generate metrics..."
foreach ($testData in $testRequests) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/redact/" -Method POST -Body $testData -Headers $headers -UseBasicParsing
        Write-Host "  ." -NoNewline -ForegroundColor Green
    } catch {
        Write-Host "  x" -NoNewline -ForegroundColor Red
    }
    Start-Sleep -Milliseconds 100
}
Write-Host ""

Write-Host ""
Write-Host "Test 3: Metrics Endpoints" -ForegroundColor Cyan

# Basic metrics
try {
    Write-Host "  Testing /metrics (basic)..."
    $metrics = Invoke-WebRequest -Uri "http://localhost:8000/metrics/" -Method GET -Headers $headers -UseBasicParsing
    $metricsData = $metrics.Content | ConvertFrom-Json
    Write-Host "  Total Requests: $($metricsData.total_requests)"
    Write-Host "  Total Redactions: $($metricsData.total_redactions)"
    Write-Host "  P95 Latency: $($metricsData.p95_latency_ms)ms"
    Write-Host "  Cache Hit Rate: $($metricsData.cache_hit_rate)%"
} catch {
    Write-Host "  Basic metrics failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Detailed metrics
try {
    Write-Host ""
    Write-Host "  Testing /metrics/detailed..."
    $detailedMetrics = Invoke-WebRequest -Uri "http://localhost:8000/metrics/detailed" -Method GET -Headers $headers -UseBasicParsing
    $detailData = $detailedMetrics.Content | ConvertFrom-Json
    Write-Host "  Health Status: $($detailData.health_status)"
    Write-Host "  Total Errors: $($detailData.total_errors)"
    Write-Host "  Min Latency: $($detailData.min_latency_ms)ms"
    Write-Host "  Max Latency: $($detailData.max_latency_ms)ms"
    
    if ($detailData.recent_alerts) {
        Write-Host "  Recent Alerts: $($detailData.recent_alerts.Count)"
    }
} catch {
    Write-Host "  Detailed metrics failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Performance metrics
try {
    Write-Host ""
    Write-Host "  Testing /metrics/performance..."
    $perfMetrics = Invoke-WebRequest -Uri "http://localhost:8000/metrics/performance" -Method GET -Headers $headers -UseBasicParsing
    $perfData = $perfMetrics.Content | ConvertFrom-Json
    Write-Host "  Throughput:"
    Write-Host "    Requests/sec: $($perfData.throughput.requests_per_second)"
    Write-Host "  Latency:"
    Write-Host "    Average: $($perfData.latency.avg_ms)ms"
    Write-Host "    P99: $($perfData.latency.p99_ms)ms"
    Write-Host "  Reliability:"
    Write-Host "    Error Rate: $($perfData.reliability.error_rate)%"
    Write-Host "    Health: $($perfData.reliability.health_status)"
} catch {
    Write-Host "  Performance metrics failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Endpoint metrics
try {
    Write-Host ""
    Write-Host "  Testing /metrics/endpoints..."
    $endpointMetrics = Invoke-WebRequest -Uri "http://localhost:8000/metrics/endpoints" -Method GET -Headers $headers -UseBasicParsing
    $epData = $endpointMetrics.Content | ConvertFrom-Json
    Write-Host "  Total Endpoints Tracked: $($epData.total_endpoints)"
    
    if ($epData.endpoints) {
        Write-Host "  Top Endpoints:"
        $count = 0
        foreach ($ep in $epData.endpoints.PSObject.Properties) {
            if ($count -ge 3) { break }
            Write-Host "    $($ep.Name): $($ep.Value.requests) requests, $($ep.Value.avg_latency_ms)ms avg"
            $count++
        }
    }
} catch {
    Write-Host "  Endpoint metrics failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Rule metrics
try {
    Write-Host ""
    Write-Host "  Testing /metrics/rules..."
    $ruleMetrics = Invoke-WebRequest -Uri "http://localhost:8000/metrics/rules" -Method GET -Headers $headers -UseBasicParsing
    $ruleData = $ruleMetrics.Content | ConvertFrom-Json
    Write-Host "  Total Rules Tracked: $($ruleData.total_rules)"
    
    if ($ruleData.rules) {
        Write-Host "  Most Triggered Rules:"
        $count = 0
        foreach ($rule in $ruleData.rules.PSObject.Properties) {
            if ($count -ge 3) { break }
            Write-Host "    $($rule.Name): $($rule.Value.total_triggers) triggers"
            $count++
        }
    }
} catch {
    Write-Host "  Rule metrics failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Test 4: Prometheus Metrics" -ForegroundColor Cyan

try {
    Write-Host "  Testing /metrics/prometheus..."
    $promMetrics = Invoke-WebRequest -Uri "http://localhost:8000/metrics/prometheus" -Method GET -UseBasicParsing
    $lines = $promMetrics.Content -split "`n"
    Write-Host "  Prometheus format metrics:"
    foreach ($line in $lines | Select-Object -First 10) {
        if ($line -and -not $line.StartsWith("#")) {
            Write-Host "    $line" -ForegroundColor Gray
        }
    }
    Write-Host "  ... ($($lines.Count) total lines)"
} catch {
    Write-Host "  Prometheus metrics failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Test 5: Alert System" -ForegroundColor Cyan

try {
    Write-Host "  Testing /metrics/alerts..."
    $alerts = Invoke-WebRequest -Uri "http://localhost:8000/metrics/alerts" -Method GET -Headers $headers -UseBasicParsing
    $alertData = $alerts.Content | ConvertFrom-Json
    Write-Host "  Total Alerts: $($alertData.total_alerts)"
    
    if ($alertData.recent_alerts -and $alertData.recent_alerts.Count -gt 0) {
        Write-Host "  Recent Alerts:" -ForegroundColor Yellow
        foreach ($alert in $alertData.recent_alerts) {
            Write-Host "    [$($alert.type)] $($alert.message)"
        }
    } else {
        Write-Host "  No alerts (system healthy)" -ForegroundColor Green
    }
} catch {
    Write-Host "  Alert retrieval failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "==================================================" -ForegroundColor Green
Write-Host "Enhanced observability tests completed!" -ForegroundColor Green
Write-Host ""
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "- Health checks: Basic, Detailed, Liveness, Readiness" -ForegroundColor White
Write-Host "- Metrics: Basic, Detailed, Performance, Endpoints, Rules" -ForegroundColor White
Write-Host "- Monitoring: Prometheus format, Alert system" -ForegroundColor White
Write-Host "- All endpoints support production monitoring tools" -ForegroundColor White