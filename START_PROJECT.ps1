#Requires -Version 5.0
param(
    [string]$Model = "mistral:7b-instruct",
    [switch]$SkipOllama
)

$ErrorActionPreference = "Continue"
$scriptPath    = $MyInvocation.MyCommand.Path
$WorkspaceRoot = Split-Path -Parent $scriptPath

# -- Self-elevate to Administrator -----------------------------------------
# Needed so taskkill can kill processes owned by any session.
# Once elevated, STOP_PROJECT runs inline -- no second UAC popup.
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    $argList = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" -Model `"$Model`""
    if ($SkipOllama) { $argList += " -SkipOllama" }
    Write-Host "Requesting Administrator privileges..." -ForegroundColor Yellow
    Start-Process powershell -Verb RunAs -ArgumentList $argList -Wait
    exit
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "   AI Assistant - Project Startup               " -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# -- Paths ------------------------------------------------------------------
$PythonExe        = "$WorkspaceRoot\.venv\Scripts\python.exe"
$BackendPath      = "$WorkspaceRoot\assistant"
$FrontendPath     = "$WorkspaceRoot\assistant\frontend"
$OllamaScript     = "$WorkspaceRoot\scripts\start_ollama.ps1"
$BackendPidFile   = "$WorkspaceRoot\.backend.pid"
$FrontendPidFile  = "$WorkspaceRoot\.frontend.pid"
$BackendLauncher  = "$WorkspaceRoot\.backend_launch.ps1"
$FrontendLauncher = "$WorkspaceRoot\.frontend_launch.ps1"

# -- Pre-flight checks -------------------------------------------------------
Write-Host "[CHECK] Verifying required components..." -ForegroundColor Yellow
$prefailed = $false

if (-not (Test-Path $PythonExe)) {
    Write-Host "  ERROR: Python venv not found at: $PythonExe" -ForegroundColor Red
    $prefailed = $true
} else { Write-Host "  OK: Python found" -ForegroundColor Green }

if (-not (Test-Path $BackendPath)) {
    Write-Host "  ERROR: Backend not found at: $BackendPath" -ForegroundColor Red
    $prefailed = $true
} else { Write-Host "  OK: Backend found" -ForegroundColor Green }

if (-not (Test-Path $FrontendPath)) {
    Write-Host "  ERROR: Frontend not found at: $FrontendPath" -ForegroundColor Red
    $prefailed = $true
} else { Write-Host "  OK: Frontend found" -ForegroundColor Green }

# Discover npm dynamically -- handles nvm, Chocolatey, and standard installs
$npmExe = (Get-Command npm -ErrorAction SilentlyContinue).Source
if (-not $npmExe) {
    Write-Host "  ERROR: npm not found in PATH. Install Node.js from https://nodejs.org" -ForegroundColor Red
    $prefailed = $true
} else { Write-Host "  OK: npm found at $npmExe" -ForegroundColor Green }

if ($prefailed) {
    Write-Host ""
    Write-Host "Pre-flight check failed. Fix the errors above and try again." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host ""

# -- Step 0: Stop any existing services -------------------------------------
# Already elevated -- STOP_PROJECT runs inline, same token, no second UAC.
Write-Host "[0] Stopping any existing services..." -ForegroundColor Yellow
& "$WorkspaceRoot\STOP_PROJECT.ps1"
Write-Host ""

# -- Step 1: Ollama ----------------------------------------------------------
if (-not $SkipOllama -and (Test-Path $OllamaScript)) {
    Write-Host "[1] Starting Ollama..." -ForegroundColor Cyan
    try { & $OllamaScript -Model $Model }
    catch { Write-Host "    Warning: Ollama failed, continuing." -ForegroundColor Yellow }
    Write-Host ""
} else {
    Write-Host "[1] Skipping Ollama." -ForegroundColor DarkGray
    Write-Host ""
}

# -- Step 2: Backend ---------------------------------------------------------
# The launcher uses TcpListener to test if port 8000 is truly bindable.
# Get-NetTCPConnection can lie (reports ghost/zombie sockets as LISTEN even
# when the owning process is dead). TcpListener.Start() never lies.
Write-Host "[2] Starting Backend (port 8000)..." -ForegroundColor Cyan

Set-Content -Path $BackendLauncher -Encoding UTF8 -Value @"
`$Host.UI.RawUI.WindowTitle = 'AI Assistant - Backend (port 8000)'
`$env:PYTHONPATH = '$BackendPath'
Set-Location '$BackendPath'
Write-Host 'Backend starting...' -ForegroundColor Cyan

# -- Wait until port 8000 is actually bindable (TcpListener never lies) ----
Write-Host 'Checking port 8000...' -ForegroundColor Yellow
`$portClear = `$false
for (`$w = 0; `$w -lt 60; `$w += 3) {
    try {
        `$l = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Any, 8000)
        `$l.Start()
        `$l.Stop()
        `$portClear = `$true
        break
    } catch {
        Write-Host "  Port 8000 occupied (`${w}s elapsed) -- killing and retrying..." -ForegroundColor Yellow
        `$foundPids = netstat -ano | Select-String '0\.0\.0\.0:8000 ' |
            ForEach-Object { (`$_.ToString().Trim() -split '\s+')[-1] } |
            Where-Object { `$_ -match '^\d+`$' -and `$_ -ne '0' } |
            Sort-Object -Unique
        foreach (`$p in `$foundPids) { cmd /c "taskkill /F /T /PID `$p" 2>`$null }
        Start-Sleep -Seconds 3
    }
}
if (-not `$portClear) {
    Write-Host '' -ForegroundColor Red
    Write-Host 'ERROR: Port 8000 could not be freed after 60s.' -ForegroundColor Red
    Write-Host 'A system reboot may be needed to clear a ghost socket.' -ForegroundColor Red
    Read-Host 'Press Enter to close'
    exit 1
}
Write-Host '  Port 8000 is free.' -ForegroundColor Green

& '$PythonExe' -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
Write-Host ''
Write-Host '=== Backend has stopped. See errors above. ===' -ForegroundColor Red
Read-Host 'Press Enter to close'
"@

# Start-Process -PassThru gives the WINDOW process object.
# We save the window PID (not python's PID). One taskkill /T kills the tree.
$backendWin = Start-Process powershell `
    -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$BackendLauncher`"" `
    -PassThru

$backendWin.Id | Set-Content $BackendPidFile
Write-Host "    Window PID $($backendWin.Id) saved to .backend.pid" -ForegroundColor Yellow
Write-Host "    Polling /health" -ForegroundColor Yellow
Start-Sleep -Seconds 6

$backendReady = $false
for ($i = 0; $i -lt 30; $i++) {
    if ($backendWin.HasExited) {
        Write-Host ""
        Write-Host "    ERROR: Backend window closed unexpectedly. Check the backend window." -ForegroundColor Red
        break
    }
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($r.StatusCode -eq 200) { $backendReady = $true; break }
    } catch { Write-Host -NoNewline "." -ForegroundColor DarkCyan }
    Start-Sleep -Seconds 1
}
Write-Host ""
if ($backendReady) {
    Write-Host "    [OK] Backend ready at http://localhost:8000" -ForegroundColor Green
} else {
    Write-Host "    [WARN] Backend not responding yet. Check its window for errors." -ForegroundColor Yellow
}
Write-Host ""

# -- Step 3: Frontend --------------------------------------------------------
Write-Host "[3] Starting Frontend (port 5173)..." -ForegroundColor Cyan

Set-Content -Path $FrontendLauncher -Encoding UTF8 -Value @"
`$Host.UI.RawUI.WindowTitle = 'AI Assistant - Frontend (port 5173)'
Set-Location '$FrontendPath'
Write-Host 'Frontend starting...' -ForegroundColor Cyan
& '$npmExe' run dev
Write-Host ''
Write-Host '=== Frontend has stopped. See errors above. ===' -ForegroundColor Red
Read-Host 'Press Enter to close'
"@

$frontendWin = Start-Process powershell `
    -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$FrontendLauncher`"" `
    -PassThru

$frontendWin.Id | Set-Content $FrontendPidFile
Write-Host "    Window PID $($frontendWin.Id) saved to .frontend.pid" -ForegroundColor Yellow
Write-Host "    Polling http://localhost:5173" -ForegroundColor Yellow
Start-Sleep -Seconds 6

$frontendReady = $false
for ($i = 0; $i -lt 40; $i++) {
    if ($frontendWin.HasExited) {
        Write-Host ""
        Write-Host "    ERROR: Frontend window closed unexpectedly. Check the frontend window." -ForegroundColor Red
        break
    }
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:5173" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($r.StatusCode -eq 200) { $frontendReady = $true; break }
    } catch { Write-Host -NoNewline "." -ForegroundColor DarkCyan }
    Start-Sleep -Seconds 1
}
Write-Host ""
if ($frontendReady) {
    Write-Host "    [OK] Frontend ready at http://localhost:5173" -ForegroundColor Green
} else {
    Write-Host "    [WARN] Frontend not responding yet (normal on first run -- Vite is building)." -ForegroundColor Yellow
}
Write-Host ""

# -- Summary ----------------------------------------------------------------
Write-Host "================================================" -ForegroundColor Green
Write-Host "   AI Assistant is Running                      " -ForegroundColor Green
Write-Host "------------------------------------------------" -ForegroundColor Green
Write-Host "   Backend  : http://localhost:8000             " -ForegroundColor Green
Write-Host "   Frontend : http://localhost:5173             " -ForegroundColor Green
Write-Host "   Ollama   : http://localhost:11434            " -ForegroundColor Green
Write-Host "------------------------------------------------" -ForegroundColor Green
Write-Host "   To STOP : run .\STOP_PROJECT.ps1             " -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""

try { Start-Process "http://localhost:5173" } catch {}

# -- EXIT -- no monitor loop ------------------------------------------------
# Services run in their own visible windows and continue independently.
# Use .\STOP_PROJECT.ps1 to shut them down.
