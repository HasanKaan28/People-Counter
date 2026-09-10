import threading
import queue
import time
import json
import os
import csv
from datetime import datetime, date
import requests

class GoogleSyncManager:
    """
    Google Drive ve Google E-Tablolar (Sheets) Senkronizasyon Yöneticisi.
    Kamera akışını ve kişi sayımını asla yavaşlatmamak için arka planda (ayrı iş parçacığında) çalışır.
    """
    def __init__(self, config):
        self.config = config
        self.queue = queue.Queue()
        self.running = True
        self.last_sync_time = 0
        self.last_status = "Hazır"
        self.last_error = None
        self.last_sync_timestamp = None

        # Arka plan senkronizasyon iş parçacığını başlat
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def update_config(self, new_config):
        self.config = new_config

    def push_update(self, stats_data, is_instant_event=False):
        """Kuyruğa yeni bir senkronizasyon paketi ekler."""
        if not self.config.get("google_sync", {}).get("enabled", False):
            # Google senkronizasyonu kapalı olsa bile yerel CSV yedeği al
            if self.config.get("google_sync", {}).get("local_csv_backup", True):
                self._save_local_csv(stats_data)
            return

        now = time.time()
        interval = self.config.get("google_sync", {}).get("sync_interval_seconds", 30)

        # Anlık giriş hareketi ise veya periyodik süre dolmuşsa kuyruğa al
        if is_instant_event or (now - self.last_sync_time >= interval):
            self.last_sync_time = now
            self.queue.put(stats_data)

    def _worker_loop(self):
        while self.running:
            try:
                # Kuyruktan veri bekle (1 saniye zaman aşımı ile)
                stats_data = self.queue.get(timeout=1.0)
                self._send_to_google_sheet(stats_data)
                self._save_local_csv(stats_data)
                self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.last_status = f"Hata: {str(e)}"
                self.last_error = str(e)
                time.sleep(2)

    def _send_to_google_sheet(self, data):
        """Google Apps Script Webhook URL'sine veri gönderir."""
        webhook_url = self.config.get("google_sync", {}).get("webhook_url", "").strip()
        if not webhook_url:
            self.last_status = "Webhook URL girilmemiş"
            return

        payload = {
            "tarih": data.get("date", date.today().strftime("%Y-%m-%d")),
            "saat": datetime.now().strftime("%H:%M:%S"),
            "yetiskin_sayisi": data.get("adult_count", 0),
            "cocuk_sayisi": data.get("child_count", 0),
            "toplam_giris": data.get("total_count", 0),
            "kisi_basi_ucret": data.get("price_per_adult", 20.0),
            "toplam_ciro_tl": data.get("total_revenue", 0.0),
            "kaynak": "Piknik Alani Tuvalet Kamerasi"
        }

        try:
            # Google Apps Script 302 yönlendirmesi yapar, allow_redirects=True şarttır
            res = requests.post(webhook_url, json=payload, timeout=10, allow_redirects=True)
            if res.status_code in [200, 302]:
                self.last_status = "Başarılı (Google Sheets Güncellendi)"
                self.last_error = None
                self.last_sync_timestamp = datetime.now().strftime("%H:%M:%S")
            else:
                self.last_status = f"Sunucu yanıtı: {res.status_code}"
        except Exception as e:
            self.last_status = f"Bağlantı hatası: {str(e)}"
            self.last_error = str(e)

    def _save_local_csv(self, data):
        """Yerel CSV yedeği oluşturur (Google Drive masaüstü klasörüne senkronize edilebilir)."""
        backup_folder = self.config.get("google_sync", {}).get("backup_folder", "gunluk_raporlar")
        os.makedirs(backup_folder, exist_ok=True)

        today_str = date.today().strftime("%Y-%m-%d")
        csv_file = os.path.join(backup_folder, f"tuvalet_sayim_{today_str}.csv")

        file_exists = os.path.exists(csv_file)
        with open(csv_file, mode="a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Tarih", "Saat", "Yetiskin", "Cocuk", "Toplam Giris", "Yetiskin Ucreti", "Toplam Ciro (TL)"])
            
            writer.writerow([
                data.get("date", today_str),
                datetime.now().strftime("%H:%M:%S"),
                data.get("adult_count", 0),
                data.get("child_count", 0),
                data.get("total_count", 0),
                data.get("price_per_adult", 20.0),
                data.get("total_revenue", 0.0)
            ])

    def get_sync_status(self):
        return {
            "enabled": self.config.get("google_sync", {}).get("enabled", False),
            "status": self.last_status,
            "last_error": self.last_error,
            "last_sync": self.last_sync_timestamp,
            "has_webhook": bool(self.config.get("google_sync", {}).get("webhook_url", "").strip())
        }

    def stop(self):
        self.running = False
