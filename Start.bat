@echo off
chcp 65001 > nul
title AI Camera People Counter & Revenue Tracker

cd /d "%~dp0"

echo =====================================================================
echo          AI CAMERA PEOPLE COUNTER & REVENUE TRACKER
echo =====================================================================
echo.

:: Check virtual environment
if not exist ".venv\Scripts\python.exe" (
    echo [NOTICE] Setup has not been completed yet.
    echo Launching the automated setup wizard...
    echo.
    call Setup.bat
    if not exist ".venv\Scripts\python.exe" (
        echo.
        echo [ERROR] Setup could not be completed. Please run Setup.bat manually.
        pause
        exit /b 1
    )
)

echo Starting application, please wait...
echo Web Dashboard: http://localhost:8000
echo.

:: Automatically open browser after 3 seconds
start "" cmd /c "timeout /t 3 /nobreak > nul & start http://localhost:8000"

:: Launch application using virtual environment python
".venv\Scripts\python.exe" app.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application exited with an error.
    pause
)
