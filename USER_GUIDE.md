# 👁️ AI Camera People Counter & Revenue Tracker - User Guide

This system monitors your Hikvision / IP RTSP security camera or USB webcam 24/7, detects and counts incoming visitors using deep learning, classifies adults and children based on configurable height thresholds, calculates total venue admission revenue in real-time, and synchronizes data to smartphones and Google Drive / Google Sheets.

---

## 🚀 1. Launching the System

### Option A: 1-Click Standalone Installer (`PeopleCounter-Setup.exe` - Recommended)
- Download and run **`PeopleCounter-Setup.exe`**.
- Click **"Install & Launch"**.
- It installs the application cleanly, creates a **"People Counter"** Desktop shortcut, and opens the live dashboard.
- From then on, simply launch via your Desktop shortcut!

### Option B: Portable Directory (`PeopleCounter.exe`)
- If using the extracted repository folder, double-click **`PeopleCounter.exe`** (or `Start.bat`).

### Option C: Linux / macOS
```bash
./start.sh
```

---

## 📹 2. Connecting Your Camera (Hikvision / RTSP / USB)

1. Click the **Settings (Gear Icon)** in the top right of the dashboard.
2. Under **Hikvision NVR / DVR Helper**:
   - Enter your NVR / Camera IP address (e.g., `192.168.1.64`).
   - Enter your camera username and password.
   - Click the camera channel number covering the entrance (Channels 1 to 8).
   - Alternatively, enter a custom RTSP URL directly:
     ```
     rtsp://admin:password@192.168.1.64:554/Streaming/Channels/102
     ```
   - *Tip:* Use channel stream `102` (sub-stream) for zero-latency 24/7 continuous operation.
   - To test with your laptop/USB webcam, enter `0`.
3. Click **Save Settings**. The live video feed will appear immediately.

---

## 🚪 3. Dual Restroom Tripwires: Same-Door Operation (Tek Kapı Giriş-Çıkış)

In public restrooms, each restroom (Men's / Women's) typically has **one doorway for both entering and exiting**:
- **Line 1 (Dış Çizgi - Outer):** Placed right in front of the door in the hallway/waiting area (near the cashier desk).
- **Line 2 (İç Çizgi - Inner):** Placed just inside the doorway.
- **Entering (Line 1 ➔ Line 2):** Counted as **GİRİŞ / ENTRY** (+1 In, +1 Inside occupancy, adds admission fee).
- **Exiting (Line 2 ➔ Line 1):** Counted as **ÇIKIŞ / EXIT** through the same door (+1 Out, -1 Inside occupancy, free of charge).

The **Live Restroom Occupancy Panel** on the dashboard displays whether each restroom is **EMPTY (BOŞ)** or **OCCUPIED (DOLU)** along with the real-time headcount inside.

### How to set the lines:
1. Click **"Edit Tripwires (2+2)"** above the camera stream.
2. Select the line you want to position:
   - 🚹 **Men Door: 1. Outer (Corridor)** & 🚹 **Men Door: 2. Inner (Restroom)**
   - 🚺 **Women Door: 1. Outer (Corridor)** & 🚺 **Women Door: 2. Inner (Restroom)**
3. Click **two points** on the video canvas (Point 1: Start, Point 2: End) for each line.
4. The system automatically saves your lines and advances to the next.
5. Click **"Default Layout"** at any time to reset to standard side-by-side lines (Left: Men, Right: Women).

---

## ⏰ 4. Scheduled Nightly Auto-Reset (Gece 00:00 Otomatik Sıfırlama)

- In **Settings**, **Scheduled Nightly Auto-Reset** is enabled by default at **00:00** (midnight).
- When midnight strikes, the system automatically:
  1. Performs a final sync of the day's turnover to Google Sheets & local archives.
  2. Clears transient tracking state and resets daily counts to 0 for the fresh day.
  3. You can customize the reset time (e.g., `04:00` or `06:00` for late-night venues) in the Settings modal anytime.

---

## 💰 5. Admission Pricing & Child Classification

- **Quick Rate:** Change the standard admission fee directly from the rate input on the revenue card.
- **Child Classification:**
  - Adjust the **Child vs Adult Height Threshold** in Settings (default: 160 pixels) according to camera mounting angle.
  - Persons whose detection bounding box height is below this value are classified as children.
  - Enable or disable **"Charge Admission for Children"** or set a discounted rate.

---

## 📱 5. Live Mobile Monitoring (Wi-Fi QR Code)

1. Click the green **"Mobile View"** button in the top right header.
2. A large QR code and local network URL (e.g., `http://192.168.1.127:8000`) will appear.
3. Scan the QR code with any smartphone connected to the same local Wi-Fi.
4. View live video, entrance counters, and turnover figures from your mobile browser without installing any app!

---

## ☁️ 6. Google Sheets & Cloud Sync

To monitor real-time visitor statistics from anywhere in the world:

1. Open [Google Drive](https://drive.google.com) and create a new **Google Spreadsheet**.
2. Click **Extensions > Apps Script** from the top menu.
3. Replace existing code with the code from `google_apps_script_template.js` in this directory.
4. Click **Deploy > New deployment**.
5. Select type **Web app**, set "Who has access" to **Anyone**, and click **Deploy**.
6. Copy the provided **Web app URL**.
7. In the People Counter dashboard, click the **Cloud Sync** button, paste the URL, check **Google Sync Active**, and click **Save**.
8. All crossing events and hourly turnover will now sync to your Google Sheet in real-time!

---

## 📁 7. Local Backups & Archiving

- Daily reports and hourly turnover statistics are automatically saved as CSV / SQLite databases in the `daily_reports` folder.
