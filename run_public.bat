@echo off
title IoT Image Gallery - Public Live Server & Tunnel
echo ========================================================
echo   Starting IoT Image Gallery with Cloudflare Public Link
echo ========================================================
echo.

:: Change directory to script folder
cd /d "%~dp0"

:: Start Flask app in background if not already running on port 5000
netstat -ano | findstr :5000 | findstr LISTENING >nul 2>&1
if %errorlevel% neq 0 (
    echo [1/2] Starting Flask backend server on port 5000...
    start "IoT Gallery Backend" /min python app.py
    timeout /t 3 /nobreak >nul
) else (
    echo [1/2] Flask backend already running on port 5000.
)

:: Start Cloudflare tunnel
echo [2/2] Starting Cloudflare Public Tunnel...
echo Look for the public https://*.trycloudflare.com URL below:
echo ========================================================
"C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://127.0.0.1:5000

pause
