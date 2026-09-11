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

## 🚪 3. Configuring Dual Restroom Tripwires (2+2 Lines)

The system uses a **Dual-Line Sequence (Line A & Line B)** for both **Men's** and **Women's** restrooms:
- **Line A:** Outer line (Dış hat - outside the doorway)
- **Line B:** Inner line (İç hat - inside the doorway)
- **Crossing Line A &rarr; Line B:** Automatically counts as **ENTRY (GİRİŞ)** (+1 In, +1 Inside occupancy, adds admission fee).
- **Crossing Line B &rarr; Line A:** Automatically counts as **EXIT (ÇIKIŞ)** (+1 Out, -1 Inside occupancy).

### How to set the lines:
1. Click **"Edit Tripwires (2+2)"** above the camera stream.
2. Select the line you want to position:
   - 🚹 **Men Line A (Outer)** & 🚹 **Men Line B (Inner)**
   - 🚺 **Women Line A (Outer)** & 🚺 **Women Line B (Inner)**
3. Click **two points** on the video canvas (Point 1: Start, Point 2: End) for each line.
4. The system automatically saves your lines and advances to the next.
5. Click **"Default Layout"** at any time to reset to standard side-by-side lines (Left: Men, Right: Women).

---

## 💰 4. Admission Pricing & Child Classification

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
