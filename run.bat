@echo off
title IoT Image Gallery - Cloud Computing
echo ========================================================
echo   Starting IoT Image Gallery...
echo   Cloud Architecture: IoT Edge Node -> S3 Raw -> Lambda Auto-Thumbnail -> S3 Thumbnails -> Gallery
echo ========================================================
echo.
start http://127.0.0.1:5000
python app.py
pause
