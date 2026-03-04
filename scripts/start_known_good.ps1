# Known-good startup script
# Freezes runtime to: Ollama mistral + backend 8000 + frontend 5173 + Edge TTS smoke/validation checks

param(
    [string]$Model = "mistral:7b-instruct",
    [switch]$SkipValidation,
    [switch]$OpenBrowser = $true
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = Split-Path -Parent $PSScriptRoot
$AssistantRoot = Join-Path $WorkspaceRoot "assistant"
$FrontendPath = Join-Path $AssistantRoot "frontend"
$PythonExe = Join-Path $WorkspaceRoot ".venv\Scripts\python.exe"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   AI Assistant - Known Good Startup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Model: $Model" -ForegroundColor Gray
Write-Host "Backend: http://localhost:8000" -ForegroundColor Gray
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Gray
Write-Host ""

if (-not (Test-Path $PythonExe)) {
    throw "Python not found at $PythonExe"
}

# STEP 1: Frontend dependency check/install
Write-Host "[01] Checking frontend dependencies..." -ForegroundColor Cyan
$env:Path += ";C:\Program Files\nodejs"
Push-Location $FrontendPath
if (-not (Test-Path (Join-Path $FrontendPath "node_modules"))) {
    Write-Host "     Installing npm dependencies..." -ForegroundColor Yellow
    npm install --legacy-peer-deps
}
Pop-Location
Write-Host "[OK] Frontend dependencies ready" -ForegroundColor Green
Write-Host ""

# STEP 2: Ensure Ollama + model are ready
Write-Host "[02] Ensuring Ollama and model are ready..." -ForegroundColor Cyan
& (Join-Path $WorkspaceRoot "scripts\start_ollama.ps1") -Model $Model
Write-Host "[OK] Ollama ready" -ForegroundColor Green
Write-Host ""

# STEP 3: Start backend
Write-Host "[03] Starting backend..." -ForegroundColor Cyan
$backendJob = Start-Job -Name "ai-backend-known-good" -ScriptBlock {
    param($AssistantDir, $PyExe)
    $env:PYTHONPATH = $AssistantDir
    & $PyExe -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --working-directory $AssistantDir
} -ArgumentList $AssistantRoot, $PythonExe

$backendReady = $false
for ($i = 0; $i -lt 45; $i++) {
    try {
        $health = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2
        if ($health.StatusCode -eq 200) {
            $backendReady = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 1
    }
}

if (-not $backendReady) {
    Stop-Job -Job $backendJob -ErrorAction SilentlyContinue
    throw "Backend failed health check on /health"
}
Write-Host "[OK] Backend healthy" -ForegroundColor Green
Write-Host ""

# STEP 4: TTS smoke test with accented Spanish
Write-Host "[04] Running Edge TTS smoke test..." -ForegroundColor Cyan
$smokeBody = '{"session_id":"known-good-smoke","actor":"user","text":"Di esta frase: José María está en Bogotá. ¿Cómo estás?","language":"es","permissions":["*"]}'
$smokeResp = Invoke-WebRequest -Uri "http://localhost:8000/chat" -Method POST -Headers @{"Content-Type"="application/json; charset=utf-8"} -Body ([System.Text.Encoding]::UTF8.GetBytes($smokeBody)) -UseBasicParsing -TimeoutSec 45
$smokeData = [System.Text.Encoding]::UTF8.GetString($smokeResp.RawContentStream.ToArray()) | ConvertFrom-Json

if (-not $smokeData.audio) {
    throw "Smoke test failed: no audio payload"
}
if ($smokeData.audio.voice_id -notlike "*DaliaNeural*") {
    throw "Smoke test failed: expected es-MX-DaliaNeural voice, got '$($smokeData.audio.voice_id)'"
}
if (-not ($smokeData.audio.audio_path -or $smokeData.audio.wav_path)) {
    throw "Smoke test failed: missing audio artifact path"
}
Write-Host "[OK] TTS smoke test passed with voice $($smokeData.audio.voice_id)" -ForegroundColor Green
Write-Host ""

# STEP 5: Full validation suite
if (-not $SkipValidation) {
    Write-Host "[05] Running validation suite..." -ForegroundColor Cyan
    Push-Location $AssistantRoot
    & $PythonExe scripts\run_validation_suite.py
    Pop-Location
    Write-Host "[OK] Validation suite completed" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "[05] Validation suite skipped" -ForegroundColor Yellow
    Write-Host ""
}

# STEP 6: Start frontend
Write-Host "[06] Starting frontend..." -ForegroundColor Cyan
$frontendJob = Start-Job -Name "ai-frontend-known-good" -ScriptBlock {
    param($Path)
    Set-Location $Path
    $env:Path += ";C:\Program Files\nodejs"
    npm run dev
} -ArgumentList $FrontendPath

$frontendReady = $false
for ($i = 0; $i -lt 40; $i++) {
    try {
        $frontend = Invoke-WebRequest -Uri "http://localhost:5173" -UseBasicParsing -TimeoutSec 2
        if ($frontend.StatusCode -eq 200) {
            $frontendReady = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 1
    }
}

if ($frontendReady) {
    Write-Host "[OK] Frontend ready at http://localhost:5173" -ForegroundColor Green
} else {
    Write-Host "[..] Frontend still starting; check job output if needed" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "============================================" -ForegroundColor Green
Write-Host "   Known-good startup completed" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

if ($OpenBrowser) {
    Start-Process "http://localhost:5173"
}

Write-Host "Press Ctrl+C to stop services" -ForegroundColor Gray

try {
    while ($true) {
        Start-Sleep -Seconds 10
        if ($backendJob.State -eq "Failed") {
            throw "Backend job failed"
        }
        if ($frontendJob.State -eq "Failed") {
            throw "Frontend job failed"
        }
    }
} finally {
    Stop-Job -Job $backendJob -ErrorAction SilentlyContinue
    Stop-Job -Job $frontendJob -ErrorAction SilentlyContinue
}
