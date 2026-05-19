# SmartBus Firewall Fix + Phone Launcher
# This script MUST run as Administrator

if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]"Administrator")) {
    Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

Write-Host "Running as Administrator - Adding firewall rules..." -ForegroundColor Green

# Remove old rules
Remove-NetFirewallRule -DisplayName "SmartBus*" -ErrorAction SilentlyContinue

# Add rules for ALL profiles (Domain, Private, Public)
New-NetFirewallRule -DisplayName "SmartBus Expo 8081"   -Direction Inbound -Protocol TCP -LocalPort 8081 -Action Allow -Profile Any
New-NetFirewallRule -DisplayName "SmartBus API 8000"    -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Any

Write-Host ""
Write-Host "SUCCESS: Ports 8000 and 8081 are now open!" -ForegroundColor Green
Write-Host ""
Write-Host "Starting Expo... QR code will appear below." -ForegroundColor Cyan
Write-Host "Scan it with Expo Go app on your phone." -ForegroundColor Cyan
Write-Host ""

# Start backend
Start-Process powershell -ArgumentList "-NoExit -Command `"cd 'C:\Users\abiha\OneDrive\Desktop\FYP_SmartBus\BMS_backend'; & 'C:\Users\abiha\OneDrive\Desktop\FYP_SmartBus\.venv\Scripts\python.exe' -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`""
Start-Sleep -Seconds 3

# Start Expo in LAN mode
Set-Location "C:\Users\abiha\OneDrive\Desktop\FYP_SmartBus\SmartBusApp"
& npx expo start --lan --port 8081
