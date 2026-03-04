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
Write-Host "[0] Cleaning up existing processes and jobs..." -ForegroundColor Yellow

# Kill old jobs first (prevents orphaned background jobs)
Get-Job -ErrorAction SilentlyContinue | Stop-Job -ErrorAction SilentlyContinue
Get-Job -ErrorAction SilentlyContinue | Remove-Job -ErrorAction SilentlyContinue

# Kill processes on ports (including Ollama on 11434)
foreach ($port in @(8000, 5173, 11434)) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($conn) {
        $pids = $conn | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($p in $pids) {
            try {
                Stop-Process -Id $p -Force -ErrorAction Stop
                Write-Host "    Killed process on port $port (PID: $p)" -ForegroundColor Yellow
            } catch {
                Write-Host "    WARNING: Could not kill PID $p on port $port" -ForegroundColor Red
                Write-Host "    You may need to run as Administrator" -ForegroundColor Red
            }
        }
    }
}

# Wait for processes to fully terminate and release ports
Start-Sleep -Seconds 2

# Verify critical ports are free with retry
$retries = 0
$maxRetries = 5
while ($retries -lt $maxRetries) {
    $conn8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
    $conn5173 = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
    
    if (-not $conn8000 -and -not $conn5173) {
        break
    }
    
    Start-Sleep -Milliseconds 500
    $retries++
}

# Final check - fail if ports still occupied
$stillOccupied = @()
if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) {
    $stillOccupied += 8000
}
if (Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue) {
    $stillOccupied += 5173
}

if ($stillOccupied.Count -gt 0) {
    Write-Host "ERROR: Ports still occupied: $($stillOccupied -join ', ')" -ForegroundColor Red
    Write-Host "Run as Administrator or manually kill processes on these ports" -ForegroundColor Red
    exit 1
}

Write-Host "    Cleanup complete - all ports free" -ForegroundColor Green
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
