@echo off
echo ===================================================
echo AI Tutor Mobile App Launcher
echo ===================================================
echo.
echo [1/3] Configuring Portable Node.js Environment...
cd /d "%~dp0"
set "NODE_DIR=%~dp0..\.tools\node-v20.11.0-win-x64"
set "PATH=%NODE_DIR%;%PATH%"

echo.
echo [2/3] Checking Dependencies...
if not exist "node_modules" (
    echo node_modules not found. Installing dependencies...
    echo (This generally requires internet access)
    call npm install
    if errorlevel 1 (
        echo.
        echo [ERROR] npm install failed. Check your internet connection.
        pause
        exit /b 1
    )
) else (
    echo Dependencies already installed.
)

echo.
echo [3/3] Starting Metro Bundler (React Native)...
echo Note: Ensure your Android Emulator is running!
echo.
call npm run android

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to start app. Please check the error above.
    pause
    exit /b 1
)

pause
