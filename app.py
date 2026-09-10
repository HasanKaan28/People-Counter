import os
import io
import time
import socket
import threading
from datetime import datetime, date

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import cv2
import qrcode

from config import load_config, save_config
import database as db
from camera_stream import HikvisionStream
from tracker import PersonTracker
from google_sync import GoogleSyncManager

# Dizin yolları
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

app = FastAPI(title="Piknik Alani Tuvalet Sayac ve Gelir Takip Sistemi")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# 1. Yapılandırma ve Servisleri Başlat
config = load_config()

# Google Senkronizasyonu
google_sync = GoogleSyncManager(config)

# Kamera Akışı (Hikvision RTSP veya Yerel Kamera)
camera = HikvisionStream(
    source=config.get("camera_source", "0"),
    rtsp_transport=config.get("rtsp_transport", "tcp")
)
camera.start()

# Kişi Takip ve Çizgi Motoru (Callback ile)
def on_entrance_event(person_type, track_id):
    """Biri kapı çizgisini içeri doğru geçtiğinde tetiklenir."""
    cfg = load_config()
    is_child = (person_type == "child")
    
    if is_child:
        fee = cfg.get("price_per_child", 0.0) if cfg.get("charge_children", False) else 0.0
    else:
        fee = cfg.get("price_per_adult", 20.0)

    # Veri tabanına kaydet
    db.record_entrance(person_type=person_type, fee=fee, track_id=track_id)

    # Güncel istatistikleri çek
    stats = db.get_today_stats(
        fee_per_adult=cfg.get("price_per_adult", 20.0),
        fee_per_child=cfg.get("price_per_child", 0.0),
        charge_children=cfg.get("charge_children", False)
    )
    tracker.set_counts(stats)

    # Google Sheets / Drive senkronizasyonunu anında tetikle
    google_sync.push_update(stats, is_instant_event=True)

tracker = PersonTracker(config, on_entrance_callback=on_entrance_event)

# Başlangıç istatistiklerini tracker'a yükle
initial_stats = db.get_today_stats(
    fee_per_adult=config.get("price_per_adult", 20.0),
    fee_per_child=config.get("price_per_child", 0.0),
    charge_children=config.get("charge_children", False)
)
tracker.set_counts(initial_stats)

def get_local_ip():
    """Bilgisayarın yerel ağ (Wi-Fi) IP adresini bulur."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# Periyodik Google Senkronizasyon Döngüsü (Arka Planda)
def periodic_sync_loop():
    while True:
        try:
            cfg = load_config()
            stats = db.get_today_stats(
                fee_per_adult=cfg.get("price_per_adult", 20.0),
                fee_per_child=cfg.get("price_per_child", 0.0),
                charge_children=cfg.get("charge_children", False)
            )
            google_sync.push_update(stats, is_instant_event=False)
        except Exception as e:
            print(f"Periyodik senkronizasyon hatası: {e}")
        time.sleep(15)

sync_thread = threading.Thread(target=periodic_sync_loop, daemon=True)
sync_thread.start()

# --- WEB & API ENDPOINTS ---

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Ana kontrol paneli arayüzü."""
    return templates.TemplateResponse(request=request, name="index.html")

def generate_video_frames():
    """Kamera karesini alır, yapay zekadan geçirir ve MJPEG olarak yayınlar."""
    while True:
        frame, is_live = camera.get_frame()
        if frame is not None:
            if is_live:
                # Yapay zeka ile insanları tespit et, takip et ve çizgiyi kontrol et
                annotated_frame, _ = tracker.process_frame(frame)
            else:
                annotated_frame = frame

            # JPEG formatına dönüştür (Kalite 75: Düşük bant genişliği, yüksek hız)
            ret, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            if ret:
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.033)  # ~30 FPS sınırı

@app.get("/video_feed")
def video_feed():
    """Canlı kamera akışı uç noktası (Web ve Telefon için)."""
    return StreamingResponse(generate_video_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/api/stats")
async def get_stats():
    """Canlı sayaç ve durum verileri."""
    cfg = load_config()
    stats = db.get_today_stats(
        fee_per_adult=cfg.get("price_per_adult", 20.0),
        fee_per_child=cfg.get("price_per_child", 0.0),
        charge_children=cfg.get("charge_children", False)
    )
    stats["camera"] = camera.get_status()
    stats["google_sync"] = google_sync.get_sync_status()
    return JSONResponse(stats)

@app.get("/api/history")
async def get_history():
    """Saatlik dağılım ve son girişler."""
    hourly = db.get_hourly_breakdown()
    recent = db.get_recent_entrances(limit=15)
    return JSONResponse({"hourly": hourly, "recent": recent})

@app.get("/api/settings")
async def get_settings():
    """Mevcut ayarları döndürür."""
    return JSONResponse(load_config())

@app.post("/api/settings")
async def update_settings(request: Request):
    """Ayarları günceller."""
    data = await request.json()
    cfg = load_config()
    
    old_source = cfg.get("camera_source")
    cfg.update(data)
    save_config(cfg)

    # Bileşenleri güncelle
    if cfg.get("camera_source") != old_source:
        camera.update_source(cfg.get("camera_source"))

    tracker.update_config(cfg)
    google_sync.update_config(cfg)

    # Güncel fiyatlarla tracker sayaçlarını senkronize et
    stats = db.get_today_stats(
        fee_per_adult=cfg.get("price_per_adult", 20.0),
        fee_per_child=cfg.get("price_per_child", 0.0),
        charge_children=cfg.get("charge_children", False)
    )
    tracker.set_counts(stats)

    return JSONResponse({"success": True, "message": "Ayarlar kaydedildi."})

@app.post("/api/reset")
async def reset_counts():
    """Bugünün sayaçlarını sıfırlar."""
    db.reset_today_data()
    cfg = load_config()
    stats = db.get_today_stats(
        fee_per_adult=cfg.get("price_per_adult", 20.0),
        fee_per_child=cfg.get("price_per_child", 0.0),
        charge_children=cfg.get("charge_children", False)
    )
    tracker.set_counts(stats)
    tracker.counted_in_ids.clear()
    tracker.counted_out_ids.clear()
    return JSONResponse({"success": True, "message": "Bugünün verileri sıfırlandı."})

@app.get("/api/mobile_url")
async def get_mobile_url():
    """Telefon ile bağlanılacak yerel URL."""
    ip = get_local_ip()
    return JSONResponse({"url": f"http://{ip}:8000"})

@app.get("/api/qr")
async def get_qr_image():
    """Telefon kamerasından okutulacak QR kod resmi üretir."""
    ip = get_local_ip()
    url = f"http://{ip}:8000"
    
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=2
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Response(content=buf.getvalue(), media_type="image/png")

@app.post("/api/test_google_sync")
async def test_google_sync():
    """Google Sheets webhook'una anında test satırı gönderir."""
    cfg = load_config()
    stats = db.get_today_stats(
        fee_per_adult=cfg.get("price_per_adult", 20.0),
        fee_per_child=cfg.get("price_per_child", 0.0),
        charge_children=cfg.get("charge_children", False)
    )
    google_sync.push_update(stats, is_instant_event=True)
    time.sleep(1.0)
    status = google_sync.get_sync_status()
    return JSONResponse({"message": f"Test sonucu: {status.get('status')}"})

if __name__ == "__main__":
    import uvicorn
    local_ip = get_local_ip()
    print("=" * 60)
    print(" KURŞUNLU PİKNİK ALANI - TUVALET TAKİP SİSTEMİ BAŞLATILDI")
    print(f" Bilgisayar Ekranı: http://localhost:8000")
    print(f" Cep Telefonu İçin: http://{local_ip}:8000")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
