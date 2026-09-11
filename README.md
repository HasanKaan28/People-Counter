# 👁️ Kamera Kişi Sayacı & Gelir Takip - AI-Powered Vision Counter & Real-Time Revenue Tracking System

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-00FFFF?logo=yolo&logoColor=black)](https://github.com/ultralytics/ultralytics)
[![OpenCV](https://img.shields.io/badge/OpenCV-Computer_Vision-5C3EE8?logo=opencv&logoColor=white)](https://opencv.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Modern_API-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/SQLite-Local_Storage-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Kamera Kişi Sayacı & Gelir Takip** is an intelligent, deep learning computer vision system designed for commercial venues, parks, and facility entrances. Utilizing Hikvision/RTSP security cameras and webcams, the system provides real-time human detection, ByteTrack trajectory tracking, adult/child height classification, and automated cashier revenue estimation based on dynamic entry tariffs.

---

## ✨ Key Capabilities

- 🧠 **Deep Learning Person Detection:** Powered by **YOLOv8** and **ByteTrack** for high-accuracy multi-object tracking across varying lighting conditions.
- 📏 **Adult vs. Child Height Classification:** Calibrated pixel-height thresholding enables differentiated counting for children and adults with customized admission pricing.
- 🚪 **Virtual Interactive Tripwire:** Interactive 2-point boundary line configurator directly on the live camera canvas, supporting directional tracking (inbound vs. outbound).
- 💰 **Automated Revenue Accounting:** Real-time revenue accumulator multiplying verified crossings by customized tariffs with live register display.
- 📱 **Local Wi-Fi Mobile Monitor (QR Code):** Scan a generated QR code from any smartphone on the local network to view zero-latency live streams, counters, and revenue stats in a mobile web dashboard.
- ☁️ **Google Sheets / Cloud Sync:** Webhook integration transmitting entrance timestamps and cumulative figures to Google Sheets / Drive in real time.
- 📑 **Automated Daily Archiving:** Hourly turnover and entrance stats automatically logged to local CSV and SQLite databases.
- 📹 **Zero-Lag RTSP Architecture:** Optimized background worker thread stream processing supporting Hikvision, Dahua, standard IP cameras, and local USB webcams.

---

## 🛠️ Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Vision & Detection** | Python 3.11, Ultralytics YOLOv8, OpenCV (cv2) |
| **Tracking Engine** | ByteTrack (state-of-the-art multi-object tracker) |
| **Server & Backend** | FastAPI / Uvicorn (HTTP + WebSocket video streaming) |
| **Frontend UI** | HTML5, CSS3, JavaScript, Canvas API |
| **Storage & Export** | SQLite3, Pandas, CSV |
| **Cloud Bridge** | Google Apps Script Webhook API |

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10 or higher
- An IP camera (Hikvision/RTSP) or standard USB webcam

### 2. Dependency Installation
```bash
# Clone repository
git clone https://github.com/HasanKaan28/kamera-kisi-sayaci.git
cd kamera-kisi-sayaci

# Install required packages
pip install -r requirements.txt
```

### 3. Execution
To launch with a single click:
- Double-click **`Baslat.bat`**.

Or via terminal:
```bash
python app.py
```
The web dashboard will automatically open in your default browser at `http://localhost:8000`.

---

## ⚙️ Configuration

Camera settings, tariff prices, and operating hours can be configured directly through the web dashboard settings modal or via `config.json`:

```json
{
  "camera_source": "0",
  "camera_name": "Hikvision Main Gate Camera",
  "price_per_adult": 20,
  "price_per_child": 0,
  "child_height_threshold": 160,
  "in_direction": "left"
}
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
