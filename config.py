import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    # Kamera Kaynagi: Hikvision RTSP adresi, yerel kamera (0) veya test video dosya yolu
    # Ornek Hikvision: "rtsp://admin:12345@192.168.1.64:554/Streaming/Channels/102"
    "camera_source": "0",
    "camera_name": "Main Entrance Camera",
    "rtsp_transport": "tcp",  # Paket kaybini onlemek icin TCP zorlamasi

    # Fiyatlandirma Ayarlari (TL)
    "price_per_adult": 20.0,   # Yetiskin giris ucreti
    "price_per_child": 0.0,    # Cocuk giris ucreti (0 ise cocuklardan ucret alinmaz)
    "charge_children": False,  # Cocuklardan ucret alinsin mi?

    # Cocuk / Yetiskin Ayrimi (Piksel Cinsinden Tespit Kutusu Boyu)
    # Kamera acisina gore tespit edilen kisinin kutu yuksekligi bu degerin altindaysa "Cocuk", ustundeyse "Yetiskin" sayilir.
    "child_height_threshold": 160,

    # Sanal Gecis Cizgisi (Tripwire) - Normallestirilmis koordinatlar (0.0 - 1.0 araligi)
    # x1, y1, x2, y2 -> Cizginin baslangic ve bitis noktalari
    "line_coords": {
        "x1": 0.1,
        "y1": 0.5,
        "x2": 0.9,
        "y2": 0.5
    },

    # Gecis Yonu: "down" (Yukardan asagi girenler = ICERI), "up", "right", "left"
    "in_direction": "down",

    # Google Sheets / Drive Canli Senkronizasyon
    "google_sync": {
        "enabled": False,
        "webhook_url": "",  # Google Apps Script Webhook URL
        "sync_interval_seconds": 30,  # Kac saniyede bir tabloya anlik veri yazilacagi
        "local_csv_backup": True,
        "backup_folder": "gunluk_raporlar"
    },

    # Calisma Saatleri (13 Saatlik Otomatik Vardiya)
    "operating_hours": {
        "enabled": False,
        "start_time": "08:00",
        "end_time": "21:00"
    },

    # Yapay Zeka Ayarlari
    "model_confidence": 0.35,
    "tracker_type": "bytetrack.yaml"
}

def load_config():
    """Yapilandirma dosyasini yukler, yoksa varsayilani olusturur."""
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Eksik anahtarlari varsayilandan tamamla
            for k, v in DEFAULT_CONFIG.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception as e:
        print(f"Ayar yukleme hatasi: {e}")
        return DEFAULT_CONFIG.copy()

def save_config(cfg):
    """Yapilandirmayi JSON dosyasina kaydeder."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Ayar kaydetme hatasi: {e}")
        return False
