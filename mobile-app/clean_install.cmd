@echo off
echo ===================================================
echo Clean Install - Fixing Dependency Issues
echo ===================================================
echo.

cd /d "%~dp0"
set "NODE_DIR=%~dp0..\\.tools\\node-v20.11.0-win-x64"
set "PATH=%NODE_DIR%;%PATH%"

echo [1/4] Stopping any running Metro processes...
taskkill /f /im node.exe 2>nul

echo.
echo [2/4] Deleting node_modules (this may take a minute)...
if exist "node_modules" (
    rmdir /s /q node_modules
    echo Deleted node_modules.
) else (
    echo node_modules not found, skipping.
)

echo.
echo [3/4] Deleting package-lock.json...
if exist "package-lock.json" (
    del /f package-lock.json
    echo Deleted package-lock.json.
)

echo.
echo [4/4] Installing fresh dependencies...
call npm install

if errorlevel 1 (
    echo.
    echo [ERROR] npm install failed.
    pause
    exit /b 1
)

echo.
echo ===================================================
echo Clean install complete! Now run start_android.cmd
echo ===================================================
pause
