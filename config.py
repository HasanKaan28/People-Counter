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

    # Dual Restroom Zones: Exactly 1 single line per door (Men & Women)
    # Optimized for overhead security cameras (Giriş ve Çıkış aynı kapıdan tek çizgiyle takip edilir):
    # - Crossing in the direction of the entry arrow = GİRİŞ (ENTRY, +1 In, +Fee, +1 Inside)
    # - Crossing in the opposite direction = ÇIKIŞ (EXIT, +1 Out, Free, -1 Inside)
    "zones": {
        "men": {
            "name": "Men's Restroom",
            "name_tr": "Erkekler Tuvaleti",
            "enabled": True,
            "line": {"x1": 0.08, "y1": 0.50, "x2": 0.42, "y2": 0.50},
            "entry_dir": 1  # 1 = downward normal (positive side is entry), -1 = upward normal
        },
        "women": {
            "name": "Women's Restroom",
            "name_tr": "Kadınlar Tuvaleti",
            "enabled": True,
            "line": {"x1": 0.58, "y1": 0.50, "x2": 0.92, "y2": 0.50},
            "entry_dir": 1
        }
    },

    # Virtual Tripwire Line - Normalized coordinates (0.0 - 1.0) (Fallback)
    "line_coords": {
        "x1": 0.1,
        "y1": 0.5,
        "x2": 0.9,
        "y2": 0.5
    },

    # Entrance Direction (Fallback)
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

    # Scheduled Auto-Reset (Daily Reset at Midnight e.g., "00:00")
    "auto_reset": {
        "enabled": True,
        "reset_time": "00:00",
        "last_reset_date": ""
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
            # Deep merge zones
            if "zones" not in data or not isinstance(data["zones"], dict):
                data["zones"] = DEFAULT_CONFIG["zones"].copy()
            else:
                for zk, zv in DEFAULT_CONFIG["zones"].items():
                    if zk not in data["zones"]:
                        data["zones"][zk] = zv.copy()
                    else:
                        zentry = data["zones"][zk]
                        if "line" not in zentry:
                            if "line_a" in zentry and "line_b" in zentry:
                                la = zentry["line_a"]
                                lb = zentry["line_b"]
                                zentry["line"] = {
                                    "x1": la.get("x1", 0.1),
                                    "y1": (la.get("y1", 0.5) + lb.get("y1", 0.5)) / 2.0,
                                    "x2": la.get("x2", 0.4),
                                    "y2": (la.get("y2", 0.5) + lb.get("y2", 0.5)) / 2.0,
                                }
                            else:
                                zentry["line"] = zv["line"].copy()
                        if "entry_dir" not in zentry:
                            zentry["entry_dir"] = 1
            # Deep merge auto_reset
            if "auto_reset" not in data or not isinstance(data["auto_reset"], dict):
                data["auto_reset"] = DEFAULT_CONFIG["auto_reset"].copy()
            else:
                for ak, av in DEFAULT_CONFIG["auto_reset"].items():
                    if ak not in data["auto_reset"]:
                        data["auto_reset"][ak] = av
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
