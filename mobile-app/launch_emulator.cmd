@echo off
echo ===================================================
echo AI Tutor Emulator Launcher
echo ===================================================
echo.
echo Found AVD: Pixel_9a
echo Starting Emulator...
echo (This window must stay open for the phone to keep running)
echo.

"C:\Users\sawan\AppData\Local\Android\Sdk\emulator\emulator.exe" -avd Pixel_9a

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to start emulator.
    echo detailed error below:
    "C:\Users\sawan\AppData\Local\Android\Sdk\emulator\emulator.exe" -avd Pixel_9a -verbose
    pause
)
