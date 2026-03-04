# Start Ollama with a model in the background

param(
    [string]$Model = "mistral:7b-instruct",
    [int]$Timeout = 60
)

Write-Host "Starting Ollama with model: $Model" -ForegroundColor Cyan

# Check if Ollama is already running
try {
    $health = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -ErrorAction SilentlyContinue
    if ($health.StatusCode -eq 200) {
        Write-Host "[OK] Ollama already running on port 11434" -ForegroundColor Green
        Write-Host "     Using existing instance..." -ForegroundColor Green
        exit 0
    }
} catch {
    # Not running, proceed with startup
}

# Start Ollama in background
Write-Host "[..] Starting Ollama service..." -ForegroundColor Yellow
try {
    Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden -ErrorAction SilentlyContinue
    Write-Host "[..] Waiting for Ollama to start..." -ForegroundColor Yellow
    
    # Wait for Ollama to be ready
    $start = Get-Date
    $ready = $false
    
    while ((Get-Date) -lt $start.AddSeconds($Timeout)) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                $ready = $true
                break
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    
    if (-not $ready) {
        Write-Host "[!!] ERROR: Ollama failed to start within $Timeout seconds" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "[OK] Ollama is ready" -ForegroundColor Green
} catch {
    Write-Host "[!!] ERROR: Failed to start Ollama: $_" -ForegroundColor Red
    exit 1
}

# Pull model if not already present
Write-Host "[..] Checking local models..." -ForegroundColor Yellow
try {
    $tags = (Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing).Content | ConvertFrom-Json
    $modelExists = $tags.models | Where-Object { $_.name -eq "$Model" } | Select-Object -First 1
    
    if ($null -eq $modelExists) {
        Write-Host "[..] Pulling model '$Model'..." -ForegroundColor Yellow
        $pullStart = Get-Date
        & ollama pull $Model 2>&1 | Select-Object -Last 1
        $pullTime = ((Get-Date) - $pullStart).TotalSeconds
        Write-Host "[OK] Model pulled in $([Math]::Round($pullTime))s" -ForegroundColor Green
    } else {
        Write-Host "[OK] Model '$Model' already available" -ForegroundColor Green
    }
} catch {
    Write-Host "[WN] Warning: Could not verify model: $_" -ForegroundColor Yellow
}

# Start the model (load it into memory)
Write-Host "[..] Loading model '$Model'..." -ForegroundColor Yellow
try {
    $loadStart = Get-Date
    
    # Send a simple request to load the model
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/generate" -Method POST `
        -Headers @{"Content-Type"="application/json"} `
        -Body (@{model=$Model; prompt="hello"; stream=$false} | ConvertTo-Json) `
        -UseBasicParsing
    
    $loadTime = ((Get-Date) - $loadStart).TotalSeconds
    Write-Host "[OK] Model loaded in $([Math]::Round($loadTime))s" -ForegroundColor Green
} catch {
    Write-Host "[!!] ERROR: Failed to load model: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[OK] Ollama is ready!" -ForegroundColor Green
Write-Host "     API: http://localhost:11434" -ForegroundColor Gray
Write-Host "     Model: $Model" -ForegroundColor Gray
Write-Host ""
exit 0
