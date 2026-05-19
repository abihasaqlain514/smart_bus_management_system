# SmartBus Dev Launcher — run this once after the emulator boots
# Usage: .\start-dev.ps1

Write-Host "SmartBus Dev Environment" -ForegroundColor Cyan
Write-Host "========================" -ForegroundColor Cyan

# ── 1. Wait for emulator to be fully online ───────────────────────────────────
Write-Host "`n[1/4] Waiting for emulator..." -ForegroundColor Yellow
$timeout = 120
$elapsed = 0
while ($elapsed -lt $timeout) {
    $devices = adb devices 2>&1 | Select-String "emulator"
    if ($devices) {
        $boot = adb shell getprop sys.boot_completed 2>&1
        if ($boot.ToString().Trim() -eq "1") {
            Write-Host "  Emulator ready!" -ForegroundColor Green
            break
        }
    }
    Start-Sleep -Seconds 3
    $elapsed += 3
}

# ── 2. Forward ports ──────────────────────────────────────────────────────────
Write-Host "`n[2/4] Forwarding ports..." -ForegroundColor Yellow
adb reverse tcp:8081 tcp:8081 | Out-Null
adb reverse tcp:8000 tcp:8000 | Out-Null
Write-Host "  Metro  8081 -> emulator OK" -ForegroundColor Green
Write-Host "  Backend 8000 -> emulator OK" -ForegroundColor Green

# ── 3. Start FastAPI backend ──────────────────────────────────────────────────
Write-Host "`n[3/4] Starting FastAPI backend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList '-NoExit', '-Command',
    'cd "c:\Users\abiha\OneDrive\Desktop\FYP_SmartBus\BMS_backend"; ' +
    'venv\Scripts\Activate.ps1; ' +
    'python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000'
Write-Host "  Backend starting on http://localhost:8000" -ForegroundColor Green

# ── 4. Start Expo Metro bundler ───────────────────────────────────────────────
Write-Host "`n[4/4] Starting Expo Metro bundler..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList '-NoExit', '-Command',
    'cd "c:\Users\abiha\OneDrive\Desktop\FYP_SmartBus\SmartBusApp"; ' +
    'npx expo start'
Write-Host "  Metro starting on port 8081" -ForegroundColor Green

# ── 5. Background port-forward watchdog (re-applies if emulator restarts) ────
Write-Host "`nStarting port-forward watchdog..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList '-WindowStyle', 'Hidden', '-Command', '
    while ($true) {
        Start-Sleep -Seconds 10
        $d = adb devices 2>&1 | Select-String "emulator"
        if ($d) {
            adb reverse tcp:8081 tcp:8081 2>&1 | Out-Null
            adb reverse tcp:8000 tcp:8000 2>&1 | Out-Null
        }
    }
'

Write-Host "`nAll done! In the Expo terminal press:" -ForegroundColor Cyan
Write-Host "  a   - open on Android emulator" -ForegroundColor White
Write-Host "  r   - reload the app" -ForegroundColor White
Write-Host "  j   - open JS debugger" -ForegroundColor White
