# STOP_PROJECT.ps1
# Kills all processes related to the AI Assistant project.
# Targets: uvicorn (port 8000), vite dev server (port 5173), ollama (port 11434),
#          and any stray python/node processes running from this workspace.

# Self-elevate to Administrator — needed to kill processes in other sessions
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Wait
    exit
}

$WorkspaceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PidFile = "$WorkspaceRoot\.running_pids"

Write-Host "`n[STOP] Stopping AI Assistant services...`n" -ForegroundColor Yellow

# ── 0. Kill by saved PIDs (most precise — written by START_PROJECT.ps1) ──────
if (Test-Path $PidFile) {
    Get-Content $PidFile | ForEach-Object {
        if ($_ -match '=(\d+)$') {
            $p = [int]$Matches[1]
            cmd /c "taskkill /F /T /PID $p" 2>$null
            Write-Host "  Killed saved PID $p ($_)" -ForegroundColor Yellow
        }
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

# ── 1. Kill by port (catches anything not in the PID file) ───────────────────
foreach ($port in @(8000, 5173, 5174, 11434)) {
    $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
             Where-Object { $_.State -in @('Listen','Established') }
    if (-not $conns) { continue }

    $owningPids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($p in $owningPids) {
        $name = (Get-Process -Id $p -ErrorAction SilentlyContinue).Name
        cmd /c "taskkill /F /T /PID $p" 2>$null
        Write-Host "  Killed PID $p ($name) on port $port" -ForegroundColor Yellow
    }
}

# ── 2. Kill any uvicorn processes anywhere on the machine ────────────────────
Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue | ForEach-Object {
    cmd /c "taskkill /F /T /PID $($_.Id)" 2>$null
    Write-Host "  Killed stray uvicorn PID $($_.Id)" -ForegroundColor Yellow
}

# ── 3. Kill python processes running from this workspace's venv ──────────────
Get-WmiObject Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.ExecutablePath -like "$WorkspaceRoot*" } |
    ForEach-Object {
        cmd /c "taskkill /F /T /PID $($_.ProcessId)" 2>$null
        Write-Host "  Killed python PID $($_.ProcessId) ($($_.CommandLine))" -ForegroundColor Yellow
    }

# ── 4. Kill node/npm processes running from this workspace ───────────────────
Get-WmiObject Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*$WorkspaceRoot*" } |
    ForEach-Object {
        cmd /c "taskkill /F /T /PID $($_.ProcessId)" 2>$null
        Write-Host "  Killed node PID $($_.ProcessId)" -ForegroundColor Yellow
    }

# ── 5. Clean up any PowerShell background jobs ───────────────────────────────
$jobs = Get-Job -ErrorAction SilentlyContinue
if ($jobs) {
    $jobs | Stop-Job -ErrorAction SilentlyContinue
    $jobs | Remove-Job -ErrorAction SilentlyContinue
    Write-Host "  Removed $($jobs.Count) background job(s)" -ForegroundColor Yellow
}

# ── 6. Confirm ports are clear ───────────────────────────────────────────────
Start-Sleep -Seconds 2
$stillBusy = @()
foreach ($port in @(8000, 5173)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        $stillBusy += $port
    }
}

if ($stillBusy.Count -eq 0) {
    Write-Host "`n[OK] All services stopped. Ports 8000 and 5173 are free.`n" -ForegroundColor Green
} else {
    Write-Host "`n[WARN] Ports still occupied: $($stillBusy -join ', ')" -ForegroundColor Red
    Write-Host "       These processes may require manual intervention.`n" -ForegroundColor Red
}
