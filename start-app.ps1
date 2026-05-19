# ============================================================
#  SmartBus Dev Launcher
#  Double-click OR run: powershell -ExecutionPolicy Bypass -File start-app.ps1
#  Starts backend, Metro bundler, port forwarding + watchdog
# ============================================================

$ROOT     = "C:\Users\abiha\OneDrive\Desktop\FYP_SmartBus"
$APP_DIR  = "$ROOT\SmartBusApp"
$BACKEND  = "$ROOT\BMS_backend"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SmartBus Dev Launcher" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Kill stale processes ───────────────────────────────────────────────
Write-Host "[1/5] Cleaning up stale processes..." -ForegroundColor Yellow
Get-Process python, node -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowTitle -notmatch "important" } |
    Stop-Process -Force -Confirm:$false -ErrorAction SilentlyContinue

$ports = @(8081, 8000)
foreach ($port in $ports) {
    $conn = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($conn) {
        $conn | Select-Object -ExpandProperty OwningProcess -Unique |
            ForEach-Object { Stop-Process -Id $_ -Force -Confirm:$false -ErrorAction SilentlyContinue }
        Write-Host "  Freed port $port"
    }
}

# ── 1b. Fix stale bus/driver statuses from last session ──────────────────
$python = "$ROOT\.venv\Scripts\python.exe"
if (Test-Path $python) {
    Set-Location $BACKEND
    & $python fix_stale_status.py 2>$null
    Set-Location $ROOT
}

# ── 2. Start FastAPI backend ──────────────────────────────────────────────
Write-Host "[2/5] Starting FastAPI backend on :8000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList '-NoExit', '-Command', @"
  Set-Location '$BACKEND'
  Write-Host 'Backend starting...' -ForegroundColor Green
  .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"@

# Wait for backend
$backendReady = $false
for ($i = 0; $i -lt 15; $i++) {
    Start-Sleep -Seconds 2
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8000/docs" -TimeoutSec 2 -ErrorAction Stop
        $backendReady = $true; break
    } catch {}
}
if ($backendReady) { Write-Host "  Backend ready at http://localhost:8000" -ForegroundColor Green }
else               { Write-Host "  Backend may still be starting — continuing..." -ForegroundColor Yellow }

# ── 3. Start Metro bundler ────────────────────────────────────────────────
Write-Host "[3/5] Starting Metro bundler on :8081..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList '-NoExit', '-Command', @"
  Set-Location '$APP_DIR'
  Write-Host 'Metro starting...' -ForegroundColor Green
  npx react-native start --port 8081
"@

# Wait for Metro
$metroReady = $false
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 2
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8081/status" -TimeoutSec 2 -ErrorAction Stop
        if ($r.Content -match "packager-status:running") { $metroReady = $true; break }
    } catch {}
}
if ($metroReady) { Write-Host "  Metro ready at http://localhost:8081" -ForegroundColor Green }
else             { Write-Host "  Metro may still be bundling — continuing..." -ForegroundColor Yellow }

# ── 4. Apply ADB port forwarding ─────────────────────────────────────────
Write-Host "[4/5] Applying ADB port forwarding..." -ForegroundColor Yellow
function Apply-AdbReverse {
    $devices = adb devices 2>&1 | Where-Object { $_ -match "emulator|device$" }
    if ($devices) {
        adb reverse tcp:8081 tcp:8081 | Out-Null
        adb reverse tcp:8000 tcp:8000 | Out-Null
        Write-Host "  adb reverse applied" -ForegroundColor Green
        return $true
    }
    Write-Host "  No device connected yet..." -ForegroundColor Yellow
    return $false
}

for ($i = 0; $i -lt 10; $i++) {
    if (Apply-AdbReverse) { break }
    Start-Sleep -Seconds 3
}

# ── 5. ADB watchdog ───────────────────────────────────────────────────────
Write-Host "[5/5] Starting ADB watchdog (re-applies port forward every 10s)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList '-NoExit', '-Command', @"
  Write-Host 'ADB Watchdog running...' -ForegroundColor Cyan
  while (`$true) {
    Start-Sleep -Seconds 10
    `$d = adb devices 2>&1 | Where-Object { `$_ -match 'emulator|device`$' }
    if (`$d) {
        adb reverse tcp:8081 tcp:8081 | Out-Null
        adb reverse tcp:8000 tcp:8000 | Out-Null
    }
  }
"@

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  All services started!" -ForegroundColor Green
Write-Host ""
Write-Host "  Backend : http://localhost:8000" -ForegroundColor White
Write-Host "  Metro   : http://localhost:8081" -ForegroundColor White
Write-Host ""
Write-Host "  On emulator: press R,R to reload" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
