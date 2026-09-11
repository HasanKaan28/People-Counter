@echo off
setlocal EnableDelayedExpansion
chcp 65001 > nul
title AI Camera People Counter - Automated Setup Wizard

cd /d "%~dp0"

echo =====================================================================
echo          AI CAMERA PEOPLE COUNTER & REVENUE TRACKER
echo                     AUTOMATED SETUP WIZARD
echo =====================================================================
echo.
echo This wizard will automatically configure your environment and
echo install all necessary AI computer vision packages.
echo.

:: ----------------------------------------------------------------------
:: STEP 1: Check Python
:: ----------------------------------------------------------------------
echo [1/4] Checking Python environment...
set "PYTHON_CMD="

python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
) else (
    py -3 --version >nul 2>&1
    if %errorlevel% equ 0 (
        set "PYTHON_CMD=py -3"
    )
)

if "%PYTHON_CMD%"=="" (
    echo.
    echo [ERROR] Python was not detected on your system!
    echo Python 3.10 or higher is required.
    echo.
    where winget >nul 2>&1
    if %errorlevel% equ 0 (
        echo Windows Package Manager (winget) detected.
        set /p INSTALL_PY="Would you like to install Python 3.11 automatically? (Y/N): "
        if /i "!INSTALL_PY!"=="Y" (
            echo.
            echo Downloading and installing Python 3.11, please wait...
            winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
            echo.
            echo [INFO] Python installed. Please restart this setup wizard.
            pause
            exit /b 0
        )
    )
    echo Opening Python download page in your browser...
    start https://www.python.org/downloads/
    echo.
    echo IMPORTANT: Make sure to check "Add python.exe to PATH" during installation.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set "DETECTED_PY=%%i"
echo Detected: !DETECTED_PY!
echo [OK] Python is available.
echo.

:: ----------------------------------------------------------------------
:: STEP 2: Virtual Environment (.venv)
:: ----------------------------------------------------------------------
echo [2/4] Setting up virtual environment (.venv)...
if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment, please wait...
    %PYTHON_CMD% -m venv .venv
    if %errorlevel% neq 0 (
        echo.
        echo [ERROR] Failed to create virtual environment (.venv).
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created successfully.
) else (
    echo [OK] Virtual environment (.venv) already exists.
)
echo.

:: ----------------------------------------------------------------------
:: STEP 3: Install Dependencies
:: ----------------------------------------------------------------------
echo [3/4] Installing AI vision and web dependencies...
echo (YOLOv8, OpenCV, FastAPI, etc. This may take a few minutes depending on your internet connection)
echo.

".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to install packages. Please check your internet connection.
    pause
    exit /b 1
)
echo.
echo [OK] All dependencies installed successfully.
echo.

:: ----------------------------------------------------------------------
:: STEP 4: Desktop Shortcut
:: ----------------------------------------------------------------------
echo [4/4] Creating Desktop shortcut...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $desktop = [Environment]::GetFolderPath('Desktop'); $s = $ws.CreateShortcut((Join-Path $desktop 'People Counter.lnk')); $s.TargetPath = (Join-Path '%~dp0' 'PeopleCounter.exe'); $s.WorkingDirectory = '%~dp0'; $s.Description = 'AI Camera People Counter & Revenue Tracker'; $s.IconLocation = 'shell32.dll,19'; $s.Save(); try { $ps = $ws.CreateShortcut('C:\Users\Public\Desktop\People Counter.lnk'); $ps.TargetPath = (Join-Path '%~dp0' 'PeopleCounter.exe'); $ps.WorkingDirectory = '%~dp0'; $ps.IconLocation = 'shell32.dll,19'; $ps.Save() } catch {}" >nul 2>&1

echo.
echo =====================================================================
echo                SETUP COMPLETED SUCCESSFULLY!
echo =====================================================================
echo.
echo You can now run the application anytime from your Desktop shortcut
echo 'People Counter' or by double-clicking 'PeopleCounter.exe'.
echo.
set /p START_NOW="Would you like to start the application now? (Y/N): "
if /i "!START_NOW!"=="Y" (
    start "" "%~dp0PeopleCounter.exe"
)
exit /b 0
