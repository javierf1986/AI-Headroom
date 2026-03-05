param(
    [string]$Model = "mistral:7b-instruct",
    [switch]$SkipOllama
)

# Self-elevate to Administrator if not already elevated.
# Without admin rights, taskkill cannot kill processes owned by other sessions.
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    $argList = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Model `"$Model`""
    if ($SkipOllama) { $argList += " -SkipOllama" }
    Start-Process powershell -Verb RunAs -ArgumentList $argList
    exit
}

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
Write-Host "[0] Cleaning up existing processes and jobs..." -ForegroundColor Yellow

# Kill old jobs first (prevents orphaned background jobs)
Get-Job -ErrorAction SilentlyContinue | Stop-Job -ErrorAction SilentlyContinue
Get-Job -ErrorAction SilentlyContinue | Remove-Job -ErrorAction SilentlyContinue

# Helper: kill all processes listening on a given port
function Kill-Port {
    param([int]$Port)
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $conn) { return }
    $owningPids = $conn | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($p in $owningPids) {
        $savedPref = $ErrorActionPreference
        $ErrorActionPreference = "SilentlyContinue"
        cmd /c "taskkill /F /T /PID $p" 2>$null
        $exitCode = $LASTEXITCODE
        $ErrorActionPreference = $savedPref
        if ($exitCode -eq 0) {
            Write-Host "    Killed process tree on port $Port (PID: $p)" -ForegroundColor Yellow
        } else {
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
            Write-Host "    Killed process on port $Port (PID: $p)" -ForegroundColor Yellow
        }
    }
}

# Kill all ports first pass
foreach ($port in @(8000, 5173, 11434)) {
    Kill-Port -Port $port
}

# Wait, then retry port 8000 until it is confirmed free (up to 15 seconds)
$elapsed = 0
while ($elapsed -lt 15) {
    Start-Sleep -Seconds 1
    $elapsed++
    $still = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
    if (-not $still) { break }
    Write-Host "    Port 8000 still occupied, retrying kill... ($elapsed s)" -ForegroundColor DarkYellow
    Kill-Port -Port 8000
}

$still8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($still8000) {
    Write-Host "    WARNING: Port 8000 still occupied after cleanup. Backend may fail to bind." -ForegroundColor Red
} else {
    Write-Host "    Port 8000 is free." -ForegroundColor Green
}

Write-Host "    Cleanup complete" -ForegroundColor Green
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

# STEP 2: Backend
Write-Host "[2] Starting Backend API..." -ForegroundColor Cyan

$backendJob = Start-Job -ScriptBlock {
    param($Path, $Exe)
    Set-Location $Path
    $env:PYTHONPATH = $Path
    & $Exe -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 2>&1
} -ArgumentList $BackendPath, $PythonExe -Name "Backend"

Write-Host "    Waiting for backend to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

$timer = 0
$ready = $false
while ($timer -lt 30) {
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
    Write-Host "    WARNING: Health check timed out, but backend may still be starting..." -ForegroundColor Yellow
    Write-Host "    Check http://localhost:8000 manually if needed" -ForegroundColor Yellow
}

Write-Host ""

# STEP 3: Frontend
Write-Host "[3] Starting Frontend..." -ForegroundColor Cyan

$env:Path = "C:\Program Files\nodejs;$env:Path"

$frontendJob = Start-Job -ScriptBlock {
    param($Path)
    Set-Location $Path
    $env:Path = "C:\Program Files\nodejs;$env:Path"
    npm run dev 2>&1
} -ArgumentList $FrontendPath -Name "Frontend"

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

# Keep running and monitor jobs
try {
    while ($true) {
        $backend = Get-Job -Name Backend -ErrorAction SilentlyContinue
        $frontend = Get-Job -Name Frontend -ErrorAction SilentlyContinue
        
        # Check for valid job states (Running or NotStarted)
        $validStates = @("Running", "NotStarted")
        
        if ($backend -and $backend.State -notin $validStates) {
            Write-Host ""
            Write-Host "ERROR: Backend job in unexpected state: $($backend.State)" -ForegroundColor Red
            $output = Receive-Job -Job $backend -ErrorAction SilentlyContinue
            if ($output) {
                Write-Host $output
            }
            break
        }
        
        if ($frontend -and $frontend.State -notin $validStates) {
            Write-Host ""
            Write-Host "ERROR: Frontend job in unexpected state: $($frontend.State)" -ForegroundColor Red
            $output = Receive-Job -Job $frontend -ErrorAction SilentlyContinue
            if ($output) {
                Write-Host $output
            }
            break
        }
        
        Start-Sleep -Seconds 5
    }
} catch {
    # Catch Ctrl+C
}

# Cleanup
Write-Host ""
Write-Host "Shutting down..." -ForegroundColor Yellow

# Stop jobs gracefully
Get-Job -ErrorAction SilentlyContinue | Stop-Job -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Force-kill any remaining processes on our ports
foreach ($port in @(8000, 5173)) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($conn) {
        $pids = $conn | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($p in $pids) {
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        }
    }
}

# Remove all jobs
Get-Job -ErrorAction SilentlyContinue | Remove-Job -ErrorAction SilentlyContinue
Write-Host "Done." -ForegroundColor Green
Write-Host ""
