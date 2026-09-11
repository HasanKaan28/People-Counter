@echo off
setlocal EnableDelayedExpansion
chcp 65001 > nul
title Kamera Kişi Sayacı - Otomatik Kurulum Sihirbazı

cd /d "%~dp0"

echo =====================================================================
echo       KAMERA KİŞİ SAYACI VE GELİR TAKİP SİSTEMİ
echo                 OTOMATİK KURULUM SİHİRBAZI
echo =====================================================================
echo.
echo Bu sihirbaz sistem için gerekli ortamı ve kütüphaneleri
echo bilgisayarınıza otomatik olarak kuracaktır.
echo.

:: ----------------------------------------------------------------------
:: 1. ADIM: Python Kontrolü
:: ----------------------------------------------------------------------
echo [1/4] Python kontrol ediliyor...
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
    echo [HATA] Bilgisayarınızda Python bulunamadı!
    echo Sistemin çalışabilmesi için Python 3.10 veya üzeri bir sürüm gereklidir.
    echo.
    where winget >nul 2>&1
    if %errorlevel% equ 0 (
        echo Windows Paket Yöneticisi (winget) tespit edildi.
        set /p INSTALL_PY="Python 3.11 otomatik olarak kurulsun mu? (E/H): "
        if /i "!INSTALL_PY!"=="E" (
            echo.
            echo Python 3.11 indiriliyor ve kuruluyor, lütfen bekleyin...
            winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
            echo.
            echo [BİLGİ] Python kurulumu tamamlandı. Ortam değişkenlerinin güncellenmesi
            echo için lütfen bu pencereyi kapatıp 'Kurulum.bat' dosyasını yeniden çalıştırın.
            echo.
            pause
            exit /b 0
        )
    )
    echo Python indirme sayfası tarayıcınızda açılıyor...
    start https://www.python.org/downloads/
    echo.
    echo ÖNEMLİ NOT: Kurulum ekranında en altta yer alan
    echo "Add python.exe to PATH" seçeneğini İŞARETLEMEYİ UNUTMAYIN!
    echo Kurulum tamamlandıktan sonra bu pencereyi kapatıp Kurulum.bat dosyasını yeniden açın.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set "DETECTED_PY=%%i"
echo Tespit edilen Python: !DETECTED_PY!
echo [OK] Python doğrulandı.
echo.

:: ----------------------------------------------------------------------
:: 2. ADIM: Sanal Ortam (.venv) Hazırlığı
:: ----------------------------------------------------------------------
echo [2/4] Sanal çalışma ortamı (.venv) hazırlanıyor...
if not exist ".venv\Scripts\python.exe" (
    echo Sanal ortam oluşturuluyor, lütfen bekleyiniz...
    %PYTHON_CMD% -m venv .venv
    if %errorlevel% neq 0 (
        echo.
        echo [HATA] Sanal ortam (.venv) oluşturulamadı!
        echo Lütfen Python kurulumunuzun tam ve çalışır durumda olduğunu kontrol edin.
        pause
        exit /b 1
    )
    echo [OK] Sanal ortam başarıyla oluşturuldu.
) else (
    echo [OK] Sanal ortam (.venv) zaten mevcut.
)
echo.

:: ----------------------------------------------------------------------
:: 3. ADIM: Bağımlılıkların Yüklenmesi
:: ----------------------------------------------------------------------
echo [3/4] Gerekli yapay zeka ve web paketleri yükleniyor...
echo (YOLOv8, OpenCV, FastAPI vb. paketler kuruluyor. Bu işlem internet hızınıza bağlı olarak birkaç dakika sürebilir)
echo.

".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo [HATA] Kütüphaneler yüklenirken bir sorun oluştu!
    echo Lütfen internet bağlantınızı kontrol edip Kurulum.bat dosyasını tekrar çalıştırın.
    pause
    exit /b 1
)
echo.
echo [OK] Tüm kütüphaneler başarıyla kuruldu.
echo.

:: ----------------------------------------------------------------------
:: 4. ADIM: Kısayol ve Yapılandırma
:: ----------------------------------------------------------------------
echo [4/4] Masaüstü başlatma kısayolu oluşturuluyor...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $d = [Environment]::GetFolderPath('Desktop'); $s = $ws.CreateShortcut((Join-Path $d 'Kamera Kisi Sayaci.lnk')); $s.TargetPath = (Join-Path '%~dp0' 'Baslat.bat'); $s.WorkingDirectory = '%~dp0'; $s.Description = 'Kamera Kişi Sayacı ve Gelir Takip Sistemi'; $s.Save()" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Masaüstünüze 'Kamera Kisi Sayaci' kısayolu başarıyla eklendi!
) else (
    echo [BİLGİ] Masaüstü kısayolu otomatik oluşturulamadı, doğrudan klasördeki 'Baslat.bat' dosyasını kullanabilirsiniz.
)

echo.
echo =====================================================================
echo                KURULUM BAŞARIYLA TAMAMLANDI!
echo =====================================================================
echo.
echo Sistemi artık masaüstünüzdeki 'Kamera Kisi Sayaci' kısayolundan
echo veya bu klasördeki 'Baslat.bat' dosyasından çalıştırabilirsiniz.
echo.
set /p START_NOW="Sistemi şimdi başlatmak ister misiniz? (E/H): "
if /i "!START_NOW!"=="E" (
    start "" "%~dp0Baslat.bat"
)
exit /b 0
