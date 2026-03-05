#Requires -Version 5.0
$ErrorActionPreference = "Continue"
$scriptPath    = $MyInvocation.MyCommand.Path
$WorkspaceRoot = Split-Path -Parent $scriptPath

# -- Self-elevate to Administrator -----------------------------------------
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Requesting Administrator privileges..." -ForegroundColor Yellow
    Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`"" -Wait
    exit
}

$BackendPidFile   = "$WorkspaceRoot\.backend.pid"
$FrontendPidFile  = "$WorkspaceRoot\.frontend.pid"
$BackendLauncher  = "$WorkspaceRoot\.backend_launch.ps1"
$FrontendLauncher = "$WorkspaceRoot\.frontend_launch.ps1"
$LegacyPidFile    = "$WorkspaceRoot\.running_pids"

Write-Host ""
Write-Host "================================================" -ForegroundColor Yellow
Write-Host "   AI Assistant - Stopping Services             " -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor Yellow
Write-Host ""

# -- 0. Kill by saved window PIDs (most precise) ---------------------------
# taskkill /F /T kills the named window process AND all its children.
if (Test-Path $BackendPidFile) {
    $bpid = [int](Get-Content $BackendPidFile -Raw).Trim()
    Write-Host "  Killing backend window (PID $bpid)..." -ForegroundColor Yellow
    cmd /c "taskkill /F /T /PID $bpid" 2>$null
    Remove-Item $BackendPidFile -Force -ErrorAction SilentlyContinue
}

if (Test-Path $FrontendPidFile) {
    $fpid = [int](Get-Content $FrontendPidFile -Raw).Trim()
    Write-Host "  Killing frontend window (PID $fpid)..." -ForegroundColor Yellow
    cmd /c "taskkill /F /T /PID $fpid" 2>$null
    Remove-Item $FrontendPidFile -Force -ErrorAction SilentlyContinue
}

# Legacy .running_pids format (old scripts wrote "backend=1234" lines)
if (Test-Path $LegacyPidFile) {
    Get-Content $LegacyPidFile | ForEach-Object {
        if ($_ -match '=(\d+)$') {
            $p = [int]$Matches[1]
            Write-Host "  Killing legacy PID $p ($_)..." -ForegroundColor Yellow
            cmd /c "taskkill /F /T /PID $p" 2>$null
        }
    }
    Remove-Item $LegacyPidFile -Force -ErrorAction SilentlyContinue
}

# -- 1. Port scan fallback --------------------------------------------------
# Catches anything still holding a port even if the PID file was stale.
Start-Sleep -Seconds 1
foreach ($port in @(8000, 5173, 5174)) {
    $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
             Where-Object { $_.State -in @('Listen', 'Established') }
    if (-not $conns) { continue }
    $owningPids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($p in $owningPids) {
        $pname = (Get-Process -Id $p -ErrorAction SilentlyContinue).Name
        Write-Host "  Killing PID $p ($pname) still on port $port..." -ForegroundColor Yellow
        cmd /c "taskkill /F /T /PID $p" 2>$null
    }
}

# -- 2. Kill any remaining venv python processes ----------------------------
Get-WmiObject Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.ExecutablePath -like "$WorkspaceRoot*" } |
    ForEach-Object {
        Write-Host "  Killing venv python (PID $($_.ProcessId))..." -ForegroundColor Yellow
        cmd /c "taskkill /F /T /PID $($_.ProcessId)" 2>$null
    }

# -- 3. Kill any remaining workspace node processes (best-effort) -----------
Get-WmiObject Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*$WorkspaceRoot*" } |
    ForEach-Object {
        Write-Host "  Killing node (PID $($_.ProcessId))..." -ForegroundColor Yellow
        cmd /c "taskkill /F /T /PID $($_.ProcessId)" 2>$null
    }

# -- 4. Clean up temp launcher files ----------------------------------------
Remove-Item $BackendLauncher  -Force -ErrorAction SilentlyContinue
Remove-Item $FrontendLauncher -Force -ErrorAction SilentlyContinue

# -- 5. Confirm ports are free -----------------------------------------------
Start-Sleep -Seconds 2
$stillBusy = @()
foreach ($port in @(8000, 5173)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        $stillBusy += $port
    }
}

Write-Host ""
if ($stillBusy.Count -eq 0) {
    Write-Host "================================================" -ForegroundColor Green
    Write-Host "   All services stopped. Ports 8000+5173 free.  " -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Green
} else {
    Write-Host "================================================" -ForegroundColor Red
    Write-Host "   WARN: Ports still busy: $($stillBusy -join ', ')  " -ForegroundColor Red
    Write-Host "   These may need manual intervention.           " -ForegroundColor Red
    Write-Host "================================================" -ForegroundColor Red
}
Write-Host ""
