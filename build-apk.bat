@echo off
title SmartBus APK Builder

set "GRADLE_USER_HOME=C:\GradleCache"
set "JAVA_HOME=C:\Program Files\Android\Android Studio\jbr"
set "PATH=%JAVA_HOME%\bin;%PATH%"

echo.
echo ============================================
echo  SmartBus APK Builder
echo  JAVA_HOME : %JAVA_HOME%
echo  GRADLE_HOME: %GRADLE_USER_HOME%
echo ============================================
echo.

cd /d "c:\Users\abiha\OneDrive\Desktop\FYP_SmartBus\SmartBusApp\android"

echo [1/2] Building APK (x86_64 only)...
call gradlew.bat app:assembleDebug -PreactNativeArchitectures=x86_64 --no-build-cache
if %ERRORLEVEL% neq 0 (
    echo.
    echo BUILD FAILED - see errors above
    pause
    exit /b 1
)

echo.
echo [2/2] Installing APK on emulator...
adb install -r "app\build\outputs\apk\debug\app-debug.apk"
if %ERRORLEVEL% neq 0 (
    echo.
    echo INSTALL FAILED - make sure emulator is running
    pause
    exit /b 1
)

echo.
echo ============================================
echo  SUCCESS! App installed with Google Maps
echo  Now press 'r' in the Metro terminal
echo ============================================
pause
