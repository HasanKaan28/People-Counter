import cv2
import time
import threading
import os
import numpy as np

class HikvisionStream:
    """
    Hikvision ve IP Kameralar icin 13 saat kesintisiz ve sifir gecikmeli (zero-lag)
    calisan guvenilir RTSP Akis Yoneticisi.
    """
    def __init__(self, source="0", rtsp_transport="tcp"):
        self.source = source
        self.rtsp_transport = rtsp_transport
        self.cap = None
        self.running = False
        self.lock = threading.Lock()
        self.latest_frame = None
        self.last_frame_time = 0
        self.fps = 0.0
        self.is_connected = False
        self.status_message = "Hazirlaniyor..."
        self.worker_thread = None

        # FFmpeg TCP ayari (RTSP paket kayiplarini onlemek icin)
        if str(self.source).startswith("rtsp"):
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = f"rtsp_transport;{self.rtsp_transport}"

    def start(self):
        """Akis is parcacigini baslatir."""
        if self.running:
            return
        self.running = True
        self.worker_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.worker_thread.start()

    def update_source(self, new_source):
        """Kamera kaynagini dinamik olarak degistirir."""
        with self.lock:
            self.source = new_source
            if str(self.source).startswith("rtsp"):
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = f"rtsp_transport;{self.rtsp_transport}"
            if self.cap:
                self.cap.release()
                self.cap = None
            self.is_connected = False
            self.status_message = "Kamera kaynagi guncellendi, baglaniyor..."

    def _open_capture(self):
        """Kamera baglantisini acar."""
        try:
            # Eger sayisal bir degerse (0, 1 gibi webcam indexi) int yap
            src = self.source
            if isinstance(src, str) and src.strip().isdigit():
                src = int(src.strip())

            if str(src).startswith("rtsp"):
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = f"rtsp_transport;{self.rtsp_transport}"
                cap = cv2.VideoCapture(src, cv2.CAP_FFMPEG)
            else:
                cap = cv2.VideoCapture(src)

            # Donanim onbellegini 1 kareye dusur (gecikmeyi onler)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    self.is_connected = True
                    self.status_message = "Kamera Bagli (Canli)"
                    return cap
            
            if cap:
                cap.release()
            return None
        except Exception as e:
            self.status_message = f"Baglanti hatasi: {str(e)}"
            return None

    def _capture_loop(self):
        """Sifir gecikmeli surekli kare okuma dongusu."""
        frame_counter = 0
        fps_timer = time.time()

        while self.running:
            if self.cap is None or not self.cap.isOpened() or not self.is_connected:
                self.status_message = f"Baglanti kuruluyor: {self.source}"
                self.cap = self._open_capture()
                if not self.is_connected:
                    time.sleep(2)  # Yeniden denemeden once bekle
                    continue

            # Kare yakala
            grabbed = self.cap.grab()
            if not grabbed:
                # Kare yakalanamadi (kamera koptu veya ag kesildi)
                self.is_connected = False
                self.status_message = "Baglanti koptu, yeniden baglaniyor..."
                if self.cap:
                    self.cap.release()
                    self.cap = None
                time.sleep(1)
                continue

            # Sadece en son kareyi bellege al
            ret, frame = self.cap.retrieve()
            if ret and frame is not None:
                now = time.time()
                with self.lock:
                    self.latest_frame = frame
                    self.last_frame_time = now
                    self.is_connected = True
                    self.status_message = "Canli Yayin Aktif"

                # FPS hesabi
                frame_counter += 1
                if now - fps_timer >= 1.0:
                    self.fps = frame_counter / (now - fps_timer)
                    frame_counter = 0
                    fps_timer = now
            else:
                self.is_connected = False
                time.sleep(0.5)

    def get_frame(self):
        """En son guncel kareyi dondurur."""
        with self.lock:
            if self.latest_frame is not None and (time.time() - self.last_frame_time < 3.0):
                return self.latest_frame.copy(), True
            else:
                # Baglanti yoksa veya kare gelmiyorsa bilgi ekrani olustur
                return self._create_placeholder_frame(), False

    def _create_placeholder_frame(self):
        """Kamera bagli degilken bilgi gosteren resim olusturur."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Koyu gri arka plan
        frame[:] = (30, 30, 35)

        # Bilgilendirme yazilari
        cv2.putText(frame, "KAMERA BAGLANTISI BEKLENIYOR", (70, 200),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 215, 255), 2, cv2.LINE_AA)
        
        info = f"Kaynak: {str(self.source)}"
        if len(info) > 45:
            info = info[:45] + "..."
        cv2.putText(frame, info, (70, 245),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)

        status = f"Durum: {self.status_message}"
        cv2.putText(frame, status, (70, 280),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (100, 180, 255), 1, cv2.LINE_AA)

        tip = "Hikvision RTSP URL'sini Ayarlar bolumunden girebilirsiniz."
        cv2.putText(frame, tip, (70, 330),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (140, 140, 140), 1, cv2.LINE_AA)

        return frame

    def get_status(self):
        return {
            "source": str(self.source),
            "connected": self.is_connected,
            "fps": round(self.fps, 1),
            "status": self.status_message
        }

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
