@echo off
title Kursunlu Piknik Alani - Tuvalet Kamera ve Gelir Takip
echo =====================================================================
echo  KURSUNLU PIKNIK ALANI - TUVALET KAMERA VE GELIR TAKIP SISTEMI
echo =====================================================================
echo.
echo Sistem baslatiliyor, lutfen bekleyiniz...
echo.

cd /d "C:\Users\ufukk\KURUNL~1\tuvalet_sayac"

set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"

if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

start "" cmd /c "timeout /t 3 /nobreak > nul & start http://localhost:8000"

"%PYTHON_EXE%" app.py

pause