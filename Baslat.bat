@echo off
chcp 65001 > nul
title Kamera Kişi Sayacı & Gelir Takip Sistemi

cd /d "%~dp0"

echo =====================================================================
echo       KAMERA KİŞİ SAYACI VE GELİR TAKİP SİSTEMİ
echo =====================================================================
echo.

:: Sanal ortam kontrolü (.venv)
if not exist ".venv\Scripts\python.exe" (
    echo [UYARI] Sistem kurulumu henüz yapılmamış veya eksik.
    echo Kurulum sihirbazı otomatik olarak başlatılıyor...
    echo.
    call Kurulum.bat
    if not exist ".venv\Scripts\python.exe" (
        echo.
        echo [HATA] Kurulum tamamlanamadı. Lütfen önce Kurulum.bat dosyasını çalıştırın.
        pause
        exit /b 1
    )
)

echo Sistem başlatılıyor, lütfen bekleyiniz...
echo Kontrol Paneli: http://localhost:8000
echo.

:: Tarayıcıyı 3 saniye sonra otomatik aç
start "" cmd /c "timeout /t 3 /nobreak > nul & start http://localhost:8000"

:: Uygulamayı sanal ortam Python ile çalıştır
".venv\Scripts\python.exe" app.py

if %errorlevel% neq 0 (
    echo.
    echo [HATA] Uygulama sonlandı veya bir hatayla karşılaşıldı.
    pause
)