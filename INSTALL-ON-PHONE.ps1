# SmartBus — Install on Phone via USB
# Run this AFTER connecting your phone with USB debugging ON

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  SmartBus Phone Installer" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

$apk = "C:\Users\abiha\OneDrive\Desktop\FYP_SmartBus\SmartBusApp\android\app\build\outputs\apk\debug\app-debug.apk"

# Wait for phone
Write-Host "`nWaiting for phone... (connect USB now)" -ForegroundColor Yellow
$phone = $null
for ($i = 0; $i -lt 30; $i++) {
    $devices = adb devices 2>&1
    $phone = $devices | Where-Object { $_ -match "\bdevice\b" -and $_ -notmatch "emulator|List" }
    if ($phone) { Write-Host "Phone found: $phone" -ForegroundColor Green; break }
    Start-Sleep -Seconds 2
    if ($i % 5 -eq 0) { Write-Host "  Still waiting... tap ALLOW on your phone popup" -ForegroundColor Gray }
}

if (-not $phone) {
    Write-Host "Phone not detected! Check USB debugging is ON." -ForegroundColor Red
    pause; exit
}

# Apply port forwarding
Write-Host "`nApplying port forwarding..." -ForegroundColor Cyan
adb -d reverse tcp:8081 tcp:8081
adb -d reverse tcp:8000 tcp:8000
Write-Host "Ports forwarded: 8081 (Metro) and 8000 (Backend)" -ForegroundColor Green

# Install APK
Write-Host "`nInstalling SmartBus APK ($([math]::Round((Get-Item $apk).Length/1MB,0)) MB)..." -ForegroundColor Cyan
adb -d install -r $apk

Write-Host "`n============================================" -ForegroundColor Green
Write-Host "  DONE! SmartBus is installed on your phone!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host "`nOpen SmartBus app on your phone now." -ForegroundColor White
Write-Host "Keep this PC connected via USB while using the app." -ForegroundColor Yellow
pause
