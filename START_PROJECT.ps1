param(
    [string]$Model = "mistral:7b-instruct",
    [switch]$SkipOllama
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "`n[*] AI Assistant - Full Project Startup`n" -ForegroundColor Cyan

# Verify paths
$PythonExe = "$WorkspaceRoot\.venv\Scripts\python.exe"
$BackendPath = "$WorkspaceRoot\assistant"
$FrontendPath = "$WorkspaceRoot\assistant\frontend"
$OllamaScript = "$WorkspaceRoot\scripts\start_ollama.ps1"

if (-not (Test-Path $PythonExe)) {
    Write-Host "ERROR: Python not found at $PythonExe" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $BackendPath)) {
    Write-Host "ERROR: Backend not found at $BackendPath" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $FrontendPath)) {
    Write-Host "ERROR: Frontend not found at $FrontendPath" -ForegroundColor Red
    exit 1
}

# STEP 0: Clean up existing jobs and processes
Write-Host "[0] Stopping any existing services..." -ForegroundColor Yellow
& "$WorkspaceRoot\STOP_PROJECT.ps1"
Write-Host "    Done" -ForegroundColor Green
Write-Host ""

# STEP 1: Ollama (optional)
if (-not $SkipOllama) {
    Write-Host "[1] Starting Ollama..." -ForegroundColor Cyan
    try {
        if (Test-Path $OllamaScript) {
            & $OllamaScript -Model $Model
        }
    } catch {
        Write-Host "    Warning: Ollama failed, continuing anyway..." -ForegroundColor Yellow
    }
    Write-Host ""
} else {
    Write-Host "[1] Skipping Ollama (--SkipOllama)" -ForegroundColor Gray
    Write-Host ""
}

# PID file — lets STOP_PROJECT kill processes directly by PID
$PidFile = "$WorkspaceRoot\.running_pids"

# STEP 2: Backend
Write-Host "[2] Starting Backend API..." -ForegroundColor Cyan

$env:PYTHONPATH = $BackendPath
$backendProc = Start-Process -FilePath $PythonExe `
    -ArgumentList "-m uvicorn backend.app:app --host 0.0.0.0 --port 8000" `
    -WorkingDirectory $BackendPath `
    -PassThru -WindowStyle Hidden

"backend=$($backendProc.Id)" | Set-Content $PidFile
Write-Host "    Backend PID: $($backendProc.Id)" -ForegroundColor Yellow
Write-Host "    Waiting for backend to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

$timer = 0
$ready = $false
while ($timer -lt 30) {
    if ($backendProc.HasExited) {
        Write-Host ""
        Write-Host "    ERROR: Backend process exited early (PID $($backendProc.Id))" -ForegroundColor Red
        break
    }
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -ErrorAction SilentlyContinue -TimeoutSec 2
        if ($resp.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
        Write-Host -NoNewline "." -ForegroundColor Cyan
    }
    $timer++
    Start-Sleep -Seconds 1
}

Write-Host ""
if ($ready) {
    Write-Host "    OK: Backend running on http://localhost:8000" -ForegroundColor Green
} else {
    Write-Host "    WARNING: Backend health check timed out" -ForegroundColor Yellow
}

Write-Host ""

# STEP 3: Frontend
Write-Host "[3] Starting Frontend..." -ForegroundColor Cyan

$nodePath = "C:\Program Files\nodejs"
$npmCmd  = "$nodePath\npm.cmd"

$frontendProc = Start-Process -FilePath $npmCmd `
    -ArgumentList "run dev" `
    -WorkingDirectory $FrontendPath `
    -PassThru -WindowStyle Hidden

"frontend=$($frontendProc.Id)" | Add-Content $PidFile
Write-Host "    Frontend PID: $($frontendProc.Id)" -ForegroundColor Yellow

Write-Host "    Waiting for frontend to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

$timer = 0
$ready = $false
while ($timer -lt 40) {
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:5173" -UseBasicParsing -ErrorAction SilentlyContinue -TimeoutSec 2
        if ($resp.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
        Write-Host -NoNewline "." -ForegroundColor Cyan
    }
    $timer++
    Start-Sleep -Seconds 1
}

Write-Host ""
if ($ready) {
    Write-Host "    OK: Frontend running on http://localhost:5173" -ForegroundColor Green
} else {
    Write-Host "    WARNING: Frontend still building (this is normal for first run)" -ForegroundColor Yellow
}

Write-Host ""

# STEP 4: Status
Write-Host "[OK] All systems ready!" -ForegroundColor Green
Write-Host ""
Write-Host "Services:" -ForegroundColor Green
Write-Host "  Backend   : http://localhost:8000" -ForegroundColor Green
Write-Host "  Frontend  : http://localhost:5173" -ForegroundColor Green
Write-Host "  Ollama    : http://localhost:11434" -ForegroundColor Green
Write-Host ""

Write-Host "Opening browser..." -ForegroundColor Yellow
Start-Sleep -Seconds 2
try {
    Start-Process "http://localhost:5173"
} catch {
    Write-Host "Could not open browser. Visit: http://localhost:5173" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Press Ctrl+C to stop all services" -ForegroundColor Gray
Write-Host ""

# Monitor until Ctrl+C
try {
    while ($true) {
        if ($backendProc.HasExited) {
            Write-Host ""
            Write-Host "ERROR: Backend process exited (code $($backendProc.ExitCode))" -ForegroundColor Red
            break
        }
        if ($frontendProc.HasExited) {
            Write-Host ""
            Write-Host "ERROR: Frontend process exited (code $($frontendProc.ExitCode))" -ForegroundColor Red
            break
        }
        Start-Sleep -Seconds 5
    }
} catch {
    # Ctrl+C
}

# Cleanup
Write-Host ""
Write-Host "Shutting down..." -ForegroundColor Yellow
& "$WorkspaceRoot\STOP_PROJECT.ps1"
Write-Host "Done." -ForegroundColor Green
Write-Host ""
