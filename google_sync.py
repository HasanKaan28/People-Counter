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
    Google Drive and Google Sheets Live Synchronization Manager.
    Runs asynchronously in a background worker thread to ensure zero impact on video stream FPS.
    """
    def __init__(self, config):
        self.config = config
        self.queue = queue.Queue()
        self.running = True
        self.last_sync_time = 0
        self.last_status = "Ready"
        self.last_error = None
        self.last_sync_timestamp = None

        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def update_config(self, new_config):
        self.config = new_config

    def push_update(self, stats_data, is_instant_event=False):
        """Pushes a new synchronization payload into the queue."""
        if not self.config.get("google_sync", {}).get("enabled", False):
            if self.config.get("google_sync", {}).get("local_csv_backup", True):
                self._save_local_csv(stats_data)
            return

        now = time.time()
        interval = self.config.get("google_sync", {}).get("sync_interval_seconds", 30)

        if is_instant_event or (now - self.last_sync_time >= interval):
            self.last_sync_time = now
            self.queue.put(stats_data)

    def _worker_loop(self):
        while self.running:
            try:
                stats_data = self.queue.get(timeout=1.0)
                self._send_to_google_sheet(stats_data)
                self._save_local_csv(stats_data)
                self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.last_status = f"Error: {str(e)}"
                self.last_error = str(e)
                time.sleep(2)

    def _send_to_google_sheet(self, data):
        """Transmits payload to Google Apps Script Webhook URL."""
        webhook_url = self.config.get("google_sync", {}).get("webhook_url", "").strip()
        if not webhook_url:
            self.last_status = "Webhook URL not configured"
            return

        men = data.get("men", {})
        women = data.get("women", {})

        payload = {
            "date": data.get("date", date.today().strftime("%Y-%m-%d")),
            "time": datetime.now().strftime("%H:%M:%S"),
            # Restroom breakdowns
            "men_in": men.get("in", 0),
            "men_out": men.get("out", 0),
            "men_inside": men.get("inside", 0),
            "men_revenue": men.get("revenue", 0.0),
            "women_in": women.get("in", 0),
            "women_out": women.get("out", 0),
            "women_inside": women.get("inside", 0),
            "women_revenue": women.get("revenue", 0.0),
            # Global totals
            "adults": data.get("adult_count", 0),
            "children": data.get("child_count", 0),
            "total_in": data.get("total_count", 0),
            "total_out": data.get("total_out", 0),
            "total_inside": data.get("total_inside", 0),
            "total_count": data.get("total_count", 0),
            "rate": data.get("price_per_adult", 20.0),
            "revenue": data.get("total_revenue", 0.0),
            "source": self.config.get("camera_name", "Restroom Corridor Camera"),
            # Backwards compatibility keys
            "tarih": data.get("date", date.today().strftime("%Y-%m-%d")),
            "saat": datetime.now().strftime("%H:%M:%S"),
            "erkek_giris": men.get("in", 0),
            "erkek_cikis": men.get("out", 0),
            "kadin_giris": women.get("in", 0),
            "kadin_cikis": women.get("out", 0),
            "toplam_giris": data.get("total_count", 0),
            "toplam_ciro_tl": data.get("total_revenue", 0.0)
        }

        try:
            res = requests.post(webhook_url, json=payload, timeout=10, allow_redirects=True)
            if res.status_code in [200, 302]:
                self.last_status = "Success (Google Sheets Synced)"
                self.last_error = None
                self.last_sync_timestamp = datetime.now().strftime("%H:%M:%S")
            else:
                self.last_status = f"Server returned status {res.status_code}"
        except Exception as e:
            self.last_status = f"Connection error: {str(e)}"
            self.last_error = str(e)

    def _save_local_csv(self, data):
        """Saves local CSV backup records."""
        backup_folder = self.config.get("google_sync", {}).get("backup_folder", "daily_reports")
        os.makedirs(backup_folder, exist_ok=True)

        today_str = date.today().strftime("%Y-%m-%d")
        csv_file = os.path.join(backup_folder, f"visitor_counts_{today_str}.csv")

        men = data.get("men", {})
        women = data.get("women", {})

        file_exists = os.path.exists(csv_file)
        with open(csv_file, mode="a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    "Date", "Time",
                    "Men IN", "Men OUT", "Men Inside", "Men Revenue",
                    "Women IN", "Women OUT", "Women Inside", "Women Revenue",
                    "Total IN", "Total OUT", "Total Inside",
                    "Adults", "Children", "Admission Rate", "Total Revenue"
                ])
            
            writer.writerow([
                data.get("date", today_str),
                datetime.now().strftime("%H:%M:%S"),
                men.get("in", 0),
                men.get("out", 0),
                men.get("inside", 0),
                men.get("revenue", 0.0),
                women.get("in", 0),
                women.get("out", 0),
                women.get("inside", 0),
                women.get("revenue", 0.0),
                data.get("total_count", 0),
                data.get("total_out", 0),
                data.get("total_inside", 0),
                data.get("adult_count", 0),
                data.get("child_count", 0),
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
