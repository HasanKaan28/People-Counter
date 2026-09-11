# 🌲 Kurşunlu Piknik Alanı - Tuvalet Kamera Sayacı ve Gelir Takip Sistemi

Bu sistem, Hikvision güvenlik kameranızı günde 13 saat kesintisiz izleyerek tuvalete giren kişileri sayar, yetişkin ve çocukları ayırt eder, belirlenen giriş ücretine göre (varsayılan 20 TL) kasaya girmesi gereken toplam parayı hesaplar ve verileri hem bilgisayarınızda hem telefonunuzda hem de Google Drive / Google E-Tablolar'da anlık gösterir.

---

## 🚀 1. Kurulum ve Başlatma (Tek Tıkla)
- **İlk Kurulum:** Klasördeki **`Kurulum.bat`** (veya `Setup.bat`) dosyasına çift tıklayın. Sistem için gerekli ortamı (`.venv`) otomatik oluşturur, kütüphaneleri yükler ve masaüstünüze başlatıcı kısayolu ekler.
- **Başlatma:** Masaüstündeki **`Kamera Kişi Sayacı`** kısayoluna veya klasördeki **`Baslat.bat`** dosyasına çift tıklayın.
- Program yapay zeka modelini ve kamerayı yükleyip otomatik olarak tarayıcınızda kontrol panelini açacaktır (`http://localhost:8000`).

---

## 📹 2. Hikvision Kameranızı Sisteme Bağlama
1. Kontrol panelinin sağ üst köşesindeki **Ayarlar (Çark)** simgesine tıklayın.
2. **Kamera RTSP Adresi** alanına Hikvision kameranızın RTSP adresini yazın:
   - Örnek Hikvision RTSP formatı:
     ```
     rtsp://admin:12345@192.168.1.64:554/Streaming/Channels/102
     ```
   - *Not:* 13 saatlik kesintisiz çalışmada bilgisayarı yormamak ve sıfır gecikme (zero-lag) elde etmek için alt akış olan `102` kanalını kullanmanız önerilir.
   - Bilgisayarınızın kendi kamerasını test etmek için bu alana sadece `0` yazabilirsiniz.
3. **Ayarları Kaydet** butonuna basın. Görüntü anında ekrana gelecektir.

---

## 🚪 3. Kapı Geçiş Çizgisini (Tripwire) Çizme
1. Kamera ekranının hemen üzerindeki **"Kapı Çizgisini Düzenle"** butonuna tıklayın.
2. Kamera görüntüsü üzerinde tuvalet kapısının veya turnikesinin eşiğini belirlemek için **2 noktaya** tıklayın (Çizginin sol/başlangıç noktası ve sağ/bitiş noktası).
3. Çizgi otomatik olarak sarı renkte çizilecektir.
4. Ayarlardan giriş yönünü seçin:
   - Yukarıdan aşağıya girenler içeri giriyorsa: **Aşağı (Down)**
   - Aşağıdan yukarıya girenler içeri giriyorsa: **Yukarı (Up)**
5. Biri bu çizgiyi geçip içeri adım attığında çizgi anlık **yeşil** yanar, sayaç 1 artar ve kasaya ücret eklenir!

---

## 💰 4. Ücret ve Ciro Ayarları
- Ana ekrandaki **Kişi Başı Ücret** kutusundan (varsayılan 20 TL) istediğiniz zaman fiyatı değiştirebilirsiniz (Örn: 25, 30 vb.).
- Fiyatı değiştirdiğinizde toplam ciro otomatik olarak güncellenir.
- **Çocuk Girişleri:**
  - Kameranın montaj yüksekliğine göre çocuk boy eşiği piksel olarak kalibre edilebilir (Varsayılan: 160 piksel).
  - Ayarlardan "Çocuklardan da Ücret Alınsın" seçeneğini açıp kapatabilir veya çocuklara özel indirimli tarife belirleyebilirsiniz.

---

## 📱 5. Cep Telefonundan Canlı İzleme (Wi-Fi)
1. Bilgisayar ekranının sağ üstündeki yeşil **"Telefonda Aç"** butonuna tıklayın.
2. Ekrana büyük bir **QR Kod** ve bağlantı adresi gelecektir (Örn: `http://192.168.1.127:8000`).
3. Piknik alanındaki Wi-Fi ağına bağlı telefonunuzun kamerasını QR koda tutun.
4. Telefonunuzda canlı kamera akışı, kişi sayaçları ve anlık kasa cirosu açılacaktır!

---

## ☁️ 6. Google Drive / Google E-Tablolar Senkronizasyonu
Piknik alanında olmasanız bile dünyanın her yerinden telefonunuzdaki **Google Drive / Google E-Tablolar** uygulamasından kasayı anlık takip etmek için:

1. [Google Drive](https://drive.google.com) hesabınızı açın ve yeni bir **Google E-Tablo** oluşturun.
2. Üst menüden **Uzantılar (Extensions) > Apps Script** seçeneğine tıklayın.
3. Açılan sayfadaki kodu silin ve klasördeki `google_apps_script_template.js` dosyasının içindeki tüm kodu oraya yapıştırın.
4. Sağ üstteki mavi **Dağıt (Deploy) > Yeni Dağıtım (New deployment)** butonuna basın.
5. Tür olarak **Web Uygulaması (Web app)** seçin; "Erişimi olanlar" kısmını **Herkes (Anyone)** yapıp **Dağıt**'a tıklayın.
6. Size verilen **Web Uygulaması URL'sini** kopyalayın.
7. Bizim programda sağ üstteki **Google Drive** butonuna tıklayıp bu URL'yi yapıştırın ve "Aktif" kutusunu işaretleyin.
8. **Artık her giriş anında telefonunuzdaki Google Drive tablonuza işlenir!**

---

## 📁 7. Yerel Yedekler
- Her günün saat saat giriş raporları ayrıca proje klasöründeki `gunluk_raporlar` klasörüne Excel/CSV olarak otomatik kaydedilir.
