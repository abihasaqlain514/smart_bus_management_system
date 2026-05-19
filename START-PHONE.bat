@echo off
title SmartBus Phone Launcher
color 0A

REM ── Request Administrator if not already running as admin ─────────────────
net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo Requesting Administrator permission - click YES on the popup...
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs -Wait"
    exit /b
)

echo.
echo  =====================================================
echo    SmartBus - Phone Launcher  ^(Running as Admin^)
echo  =====================================================
echo.

REM ── Step 1: Open firewall ports ──────────────────────────────────────────
echo  [1/3] Opening firewall ports 8000 and 8081...
netsh advfirewall firewall delete rule name="SmartBus-8081" >nul 2>&1
netsh advfirewall firewall delete rule name="SmartBus-8000" >nul 2>&1
netsh advfirewall firewall add rule name="SmartBus-8081" dir=in action=allow protocol=TCP localport=8081 profile=any >nul
netsh advfirewall firewall add rule name="SmartBus-8000" dir=in action=allow protocol=TCP localport=8000 profile=any >nul
echo  Ports opened successfully.
echo.

REM ── Step 2: Start backend ─────────────────────────────────────────────────
echo  [2/3] Starting FastAPI Backend on port 8000...
start "SmartBus Backend" cmd /k "cd /d C:\Users\abiha\OneDrive\Desktop\FYP_SmartBus\BMS_backend && C:\Users\abiha\OneDrive\Desktop\FYP_SmartBus\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 4 /nobreak >nul
echo  Backend started.
echo.

REM ── Step 3: Start Expo ───────────────────────────────────────────────────
echo  [3/3] Starting Expo - QR code will appear below...
echo.
echo  =====================================================
echo   Phone setup:
echo     WiFi IP    : 192.168.10.4
echo     Backend    : http://192.168.10.4:8000
echo     Expo URL   : exp://192.168.10.4:8081
echo.
echo   MAKE SURE your phone is on the same WiFi!
echo  =====================================================
echo.
cd /d C:\Users\abiha\OneDrive\Desktop\FYP_SmartBus\SmartBusApp
npx expo start --lan --port 8081

pause
