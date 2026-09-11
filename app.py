import os
import io
import time
import socket
import threading
from datetime import datetime, date

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import cv2
import qrcode

from config import load_config, save_config
import database as db
from camera_stream import HikvisionStream
from tracker import PersonTracker
from google_sync import GoogleSyncManager

# Directory paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

app = FastAPI(title="AI Camera People Counter & Revenue Tracker")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# 1. Load Configuration & Initialize Services
config = load_config()

# Cloud Synchronization Manager
google_sync = GoogleSyncManager(config)

# Camera Video Stream
camera = HikvisionStream(
    source=config.get("camera_source", "0"),
    rtsp_transport=config.get("rtsp_transport", "tcp")
)
camera.start()

# Person Tracking Engine with Crossing Callback
def on_tracker_event(zone, direction, person_type, track_id):
    """Triggered upon verified tripwire crossing in Men or Women zone (IN or OUT)."""
    cfg = load_config()
    is_child = (person_type == "child")
    
    if direction == "in":
        if is_child:
            fee = cfg.get("price_per_child", 0.0) if cfg.get("charge_children", False) else 0.0
        else:
            fee = cfg.get("price_per_adult", 20.0)
    else:
        fee = 0.0

    # Persist event to database
    db.record_event(zone=zone, direction=direction, person_type=person_type, fee=fee, track_id=track_id)

    # Fetch updated daily metrics
    stats = db.get_today_stats(
        fee_per_adult=cfg.get("price_per_adult", 20.0),
        fee_per_child=cfg.get("price_per_child", 0.0),
        charge_children=cfg.get("charge_children", False)
    )
    tracker.set_counts(stats)

    # Trigger immediate cloud sync
    if direction == "in":
        google_sync.push_update(stats, is_instant_event=True)

tracker = PersonTracker(config, on_event_callback=on_tracker_event)

# Initialize tracker with existing daily stats
initial_stats = db.get_today_stats(
    fee_per_adult=config.get("price_per_adult", 20.0),
    fee_per_child=config.get("price_per_child", 0.0),
    charge_children=config.get("charge_children", False)
)
tracker.set_counts(initial_stats)

def get_local_ip():
    """Resolves the local network (Wi-Fi) IP address of the machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# Periodic Cloud Sync Loop (Background Thread)
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
            print(f"Periodic sync error: {e}")
        time.sleep(15)

sync_thread = threading.Thread(target=periodic_sync_loop, daemon=True)
sync_thread.start()

# Scheduled Nightly Auto-Reset Loop (Background Thread)
def scheduled_auto_reset_loop():
    while True:
        try:
            cfg = load_config()
            auto_cfg = cfg.get("auto_reset", {})
            if auto_cfg.get("enabled", True):
                reset_time = auto_cfg.get("reset_time", "00:00")
                now_str = datetime.now().strftime("%H:%M")
                today_str = datetime.now().strftime("%Y-%m-%d")
                last_reset = auto_cfg.get("last_reset_date", "")

                if now_str == reset_time and last_reset != today_str:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [AUTO-RESET] Triggering daily auto-reset ({reset_time})...")
                    # 1. Final cloud sync before reset
                    stats = db.get_today_stats(
                        fee_per_adult=cfg.get("price_per_adult", 20.0),
                        fee_per_child=cfg.get("price_per_child", 0.0),
                        charge_children=cfg.get("charge_children", False)
                    )
                    google_sync.push_update(stats, is_instant_event=False)

                    # 2. Reset today's database records and in-memory tracker state
                    db.reset_today_data()
                    fresh_stats = db.get_today_stats(
                        fee_per_adult=cfg.get("price_per_adult", 20.0),
                        fee_per_child=cfg.get("price_per_child", 0.0),
                        charge_children=cfg.get("charge_children", False)
                    )
                    tracker.set_counts(fresh_stats)
                    tracker.zone_cross_state.clear()
                    tracker.event_cooldown.clear()
                    tracker.last_line_hit.clear()
                    tracker.counted_in_ids.clear()
                    tracker.counted_out_ids.clear()

                    # 3. Update last reset date
                    cfg["auto_reset"]["last_reset_date"] = today_str
                    save_config(cfg)
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [AUTO-RESET] Daily reset completed successfully.")
        except Exception as e:
            print(f"Auto-reset loop error: {e}")
        time.sleep(25)

reset_thread = threading.Thread(target=scheduled_auto_reset_loop, daemon=True)
reset_thread.start()

# --- WEB & API ENDPOINTS ---

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main dashboard interface."""
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/favicon.ico")
async def get_favicon():
    """Serves the application icon."""
    ico_path = os.path.join(BASE_DIR, "app.ico")
    if os.path.exists(ico_path):
        return FileResponse(ico_path, media_type="image/x-icon")
    return Response(status_code=204)

def generate_video_frames():
    """Captures camera frame, applies AI tracking, and yields MJPEG stream."""
    while True:
        frame, is_live = camera.get_frame()
        if frame is not None:
            if is_live:
                annotated_frame, _ = tracker.process_frame(frame)
            else:
                annotated_frame = frame

            # Encode as JPEG (Quality 75 for optimal responsiveness and bandwidth)
            ret, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            if ret:
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.033)  # ~30 FPS throttle

@app.get("/video_feed")
def video_feed():
    """Live MJPEG video feed endpoint."""
    return StreamingResponse(generate_video_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/api/stats")
async def get_stats():
    """Live metric counters and system status."""
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
    """Hourly traffic breakdown and recent events."""
    hourly = db.get_hourly_breakdown()
    recent = db.get_recent_entrances(limit=15)
    return JSONResponse({"hourly": hourly, "recent": recent})

@app.get("/api/settings")
async def get_settings():
    """Returns active configuration."""
    return JSONResponse(load_config())

@app.post("/api/settings")
async def update_settings(request: Request):
    """Updates system configuration."""
    data = await request.json()
    cfg = load_config()
    
    old_source = cfg.get("camera_source")
    cfg.update(data)
    save_config(cfg)

    # Update components dynamically
    if cfg.get("camera_source") != old_source:
        camera.update_source(cfg.get("camera_source"))

    tracker.update_config(cfg)
    google_sync.update_config(cfg)

    stats = db.get_today_stats(
        fee_per_adult=cfg.get("price_per_adult", 20.0),
        fee_per_child=cfg.get("price_per_child", 0.0),
        charge_children=cfg.get("charge_children", False)
    )
    tracker.set_counts(stats)

    return JSONResponse({"success": True, "message": "Settings saved successfully."})

@app.post("/api/reset")
async def reset_counts():
    """Resets counters for the current day."""
    db.reset_today_data()
    cfg = load_config()
    stats = db.get_today_stats(
        fee_per_adult=cfg.get("price_per_adult", 20.0),
        fee_per_child=cfg.get("price_per_child", 0.0),
        charge_children=cfg.get("charge_children", False)
    )
    tracker.set_counts(stats)
    tracker.zone_cross_state.clear()
    tracker.event_cooldown.clear()
    tracker.last_line_hit.clear()
    tracker.counted_in_ids.clear()
    tracker.counted_out_ids.clear()
    return JSONResponse({"success": True, "message": "Daily metrics reset successfully."})

@app.get("/api/mobile_url")
async def get_mobile_url():
    """Local network URL for mobile browser access."""
    ip = get_local_ip()
    return JSONResponse({"url": f"http://{ip}:8000"})

@app.get("/api/qr")
async def get_qr_image():
    """Generates QR code image for instant smartphone connectivity."""
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
    """Sends test record to Google Sheets webhook."""
    cfg = load_config()
    stats = db.get_today_stats(
        fee_per_adult=cfg.get("price_per_adult", 20.0),
        fee_per_child=cfg.get("price_per_child", 0.0),
        charge_children=cfg.get("charge_children", False)
    )
    google_sync.push_update(stats, is_instant_event=True)
    time.sleep(1.0)
    status = google_sync.get_sync_status()
    return JSONResponse({"message": f"Sync status: {status.get('status')}"})

if __name__ == "__main__":
    import uvicorn
    local_ip = get_local_ip()
    print("=" * 65)
    print(" AI CAMERA PEOPLE COUNTER & REVENUE TRACKER")
    print(f" Web Dashboard: http://localhost:8000")
    print(f" Mobile View:   http://{local_ip}:8000")
    print("=" * 65)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
