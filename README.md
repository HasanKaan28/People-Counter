# 🌲 Kurşunlu Piknik Alanı - Yapay Zeka Destekli Kamera Sayacı ve Gelir Takip Sistemi

Hikvision güvenlik kameraları ve RTSP video akışları üzerinden derin öğrenme (YOLOv8 & ByteTrack) ile insan geçişlerini sayan, yetişkin/çocuk ayrımı yapan ve kasaya giren ciroyu anlık hesaplayan akıllı izleme ve raporlama sistemi.

Web arayüzü sayesinde yerel ağdan veya cep telefonundan anlık olarak canlı izlenebilir ve veriler otomatik olarak Google Drive / E-Tablolar'a senkronize edilir.

---

## ✨ Öne Çıkan Özellikler

- 👁️ **Yapay Zekalı Kişi Algılama & Takip:** YOLOv8 derin öğrenme mimarisi ve ByteTrack algoritmasıyla yüksek doğrulukta kişi sayımı.
- 📏 **Yetişkin & Çocuk Ayrımı:** Kamera açısına göre kalibre edilebilen piksel boy eşiği ile çocuk ve yetişkin geçişlerini ayrı tespit etme.
- 🚪 **Sanal Kapı Çizgisi (Tripwire):** Arayüz üzerinden tek tıkla kapı/turnike eşiğine sanal çizgi çekme ve yön tayini (giriş/çıkış yönü).
- 💰 **Otomatik Kasa & Ciro Hesabı:** Kişi başı ücret tarifesine göre gerçek zamanlı toplam kazanç hesaplama.
- 📱 **Mobil Canlı İzleme (QR Kod):** Yerel Wi-Fi ağı üzerindeki herhangi bir telefondan QR kod okutarak anlık kamera ve ciro takibi.
- ☁️ **Google Drive & E-Tablolar Entegrasyonu:** Giriş verilerini ve günlük hasılatı anında bulut tablosuna aktarma.
- 📑 **Günlük Excel / CSV Raporları:** Her günün saatlik dökümünü otomatik arşivleme.
- 📹 **RTSP & Web Kamerası Desteği:** Hikvision, Dahua veya standart IP/USB kameralarla tam uyumlu çalışma.

---

## 🛠️ Kullanılan Teknolojiler

- **Yapay Zeka & Görüntü İşleme:** Python 3.11, OpenCV, Ultralytics YOLOv8, ByteTrack
- **Backend & Sunucu:** FastAPI / Uvicorn (veya Flask)
- **Arayüz:** HTML5, Modern CSS, WebSocket tabanlı canlı video akışı
- **Veritabanı & Depolama:** SQLite, Pandas, CSV
- **Bulut:** Google Apps Script Webhook API

---

## 🚀 Kurulum ve Çalıştırma

### 1. Gereksinimler
- Python 3.10+
- Bir RTSP destekli IP kamera (Hikvision vb.) veya bilgisayar web kamerası

### 2. Bağımlılıkları Yükleme
```bash
pip install -r requirements.txt
```

### 3. Başlatma
Tek tıkla başlatmak için:
- **`Baslat.bat`** dosyasına çift tıklayın.

Veya terminalden:
```bash
python app.py
```
Tarayıcınızda `http://localhost:8000` adresi otomatik açılacaktır.

---

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır.
