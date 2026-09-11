# 👁️ AI Camera People Counter & Revenue Tracker

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-00FFFF?logo=yolo&logoColor=black)](https://github.com/ultralytics/ultralytics)
[![OpenCV](https://img.shields.io/badge/OpenCV-Computer_Vision-5C3EE8?logo=opencv&logoColor=white)](https://opencv.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Modern_API-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/SQLite-Local_Storage-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**AI Camera People Counter & Revenue Tracker** is an intelligent computer vision system designed for parks, venues, retail stores, and commercial entrances. Utilizing Hikvision/RTSP security cameras, IP streams, or USB webcams, the system provides real-time human detection, ByteTrack trajectory tracking, adult/child height classification, and automated cashier revenue estimation based on configurable tariffs.

The web interface defaults to **English** and includes an instant **Language Switcher (English / Turkish)** right from the navigation bar.

---

## ✨ Key Capabilities

- 🚻 **Dual-Zone Restroom Tracking (Men & Women):** Track Men's and Women's restrooms simultaneously on a single camera view, with dedicated counters and live inside occupancy metrics.
- 🚪 **Bidirectional Same-Door Tracking:** For restrooms where visitors enter and exit through the same doorway, single-line overhead tripwire tracking with arrow directional vectoring differentiates entries from exits. Entering in the arrow direction charges the fee and increments occupancy; exiting opposite the arrow is free and decrements occupancy.
- 🟢 **Live Restroom Occupancy Panel:** Dedicated real-time dashboard component displaying `EMPTY` or `OCCUPIED` status with exact headcounts inside each restroom.
- ⏰ **Scheduled Nightly Auto-Reset:** Automatically archives the day's turnover and visitor counts to the database / Google Sheets at midnight (00:00) and resets the counter for the fresh day.
- 🧠 **Deep Learning Person Detection:** Powered by **YOLOv8** and **ByteTrack** for high-accuracy multi-object tracking across varying lighting conditions.
- 📏 **Adult vs. Child Height Classification:** Calibrated pixel-height thresholding enables differentiated counting for children and adults with customized admission pricing.
- 💰 **Automated Revenue Accounting:** Real-time revenue accumulator multiplying verified crossings by customized tariffs with live register display.
- 🌐 **Bilingual Support (EN / TR):** Clean English interface by default with a one-click toggle to Turkish.
- 📱 **Local Wi-Fi Mobile Monitor (QR Code):** Scan a generated QR code from any smartphone on the local network to view zero-latency live streams, counters, and revenue stats in a mobile web dashboard.
- ☁️ **Google Sheets / Cloud Sync:** Webhook integration transmitting entrance timestamps and cumulative figures to Google Sheets / Drive in real time.
- 📑 **Automated Daily Archiving:** Hourly turnover and entrance stats automatically logged to local CSV and SQLite databases.
- 📹 **Zero-Lag RTSP Architecture:** Optimized background worker thread stream processing supporting Hikvision, Dahua, standard IP cameras, and local USB webcams.

---

## 🛠️ Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Vision & Detection** | Python 3.10+, Ultralytics YOLOv8, OpenCV (cv2) |
| **Tracking Engine** | ByteTrack (multi-object tracker) |
| **Server & Backend** | FastAPI / Uvicorn (HTTP + WebSocket video streaming) |
| **Frontend UI** | HTML5, Tailwind CSS, JavaScript, Canvas API, Chart.js |
| **Storage & Export** | SQLite3, CSV |
| **Cloud Bridge** | Google Apps Script Webhook API |

---

## 🚀 Quick Start

### 1. Windows (1-Click Standalone Installer - Recommended)
1. Download **[`PeopleCounter-Setup.exe`](https://github.com/HasanKaan28/kamera-kisi-sayaci/releases/latest/download/PeopleCounter-Setup.exe)**.
2. Double-click **`PeopleCounter-Setup.exe`** and click **"Install & Launch"**:
   - Automatically unpacks all files to a clean application folder (`AppData\Local\Programs\PeopleCounter`).
   - Automatically configures the Python virtual environment and installs all AI vision packages.
   - Creates a **"People Counter"** shortcut on your Desktop.
   - Immediately starts the computer vision server and opens `http://localhost:8000` in your browser.
3. Once installed, simply double-click the **"People Counter"** icon on your Desktop anytime!

---

### 2. Linux / macOS
```bash
# Setup
chmod +x install.sh start.sh
./install.sh

# Launch
./start.sh
```

---

### 3. Manual Terminal Setup
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```
The dashboard will open automatically in your browser at `http://localhost:8000`.

---

## ⚙️ Configuration

Camera settings, tariff prices, and operating hours can be configured directly through the web dashboard settings modal or via `config.json`:

```json
{
  "camera_source": "0",
  "camera_name": "Main Entrance Camera",
  "price_per_adult": 20,
  "price_per_child": 0,
  "child_height_threshold": 160,
  "in_direction": "down"
}
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
