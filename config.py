import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    # Camera Source: RTSP stream URL, local webcam index (0), or video file path
    # Example Hikvision: "rtsp://admin:12345@192.168.1.64:554/Streaming/Channels/102"
    "camera_source": "0",
    "camera_name": "Main Entrance Camera",
    "rtsp_transport": "tcp",  # Force TCP to prevent packet drop in RTSP streams

    # Admission Pricing Configuration
    "price_per_adult": 20.0,   # Standard admission rate
    "price_per_child": 0.0,    # Child admission rate (0 = free entry for accompanied minors)
    "charge_children": False,  # Whether to charge children

    # Child vs. Adult Height Threshold (Bounding Box Height in Pixels)
    # Calibrated according to camera mounting angle
    "child_height_threshold": 160,

    # Virtual Tripwire Line - Normalized coordinates (0.0 - 1.0)
    # x1, y1, x2, y2 -> Start and end points of the tripwire
    "line_coords": {
        "x1": 0.1,
        "y1": 0.5,
        "x2": 0.9,
        "y2": 0.5
    },

    # Entrance Direction: "down" (top-to-bottom = IN), "up", "right", "left"
    "in_direction": "down",

    # Google Sheets / Cloud Sync
    "google_sync": {
        "enabled": False,
        "webhook_url": "",  # Google Apps Script Webhook URL
        "sync_interval_seconds": 30,
        "local_csv_backup": True,
        "backup_folder": "daily_reports"
    },

    # Operating Hours
    "operating_hours": {
        "enabled": False,
        "start_time": "08:00",
        "end_time": "21:00"
    },

    # AI Model Settings
    "model_confidence": 0.35,
    "tracker_type": "bytetrack.yaml"
}

def load_config():
    """Loads configuration from JSON file or generates defaults."""
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return DEFAULT_CONFIG.copy()

def save_config(cfg):
    """Saves configuration dictionary to JSON file."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Error saving configuration: {e}")
        return False
