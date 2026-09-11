import cv2
import time
import threading
import os
import numpy as np

class HikvisionStream:
    """
    High-performance RTSP / USB webcam video capture manager
    engineered for zero-latency 24/7 continuous operation.
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
        self.status_message = "Initializing..."
        self.worker_thread = None

        # Force TCP transport for RTSP streams to eliminate packet loss artifacts
        if str(self.source).startswith("rtsp"):
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = f"rtsp_transport;{self.rtsp_transport}"

    def start(self):
        """Starts background frame ingestion worker thread."""
        if self.running:
            return
        self.running = True
        self.worker_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.worker_thread.start()

    def update_source(self, new_source):
        """Dynamically updates the video source."""
        with self.lock:
            self.source = new_source
            if str(self.source).startswith("rtsp"):
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = f"rtsp_transport;{self.rtsp_transport}"
            if self.cap:
                self.cap.release()
                self.cap = None
            self.is_connected = False
            self.status_message = "Video source updated, connecting..."

    def _open_capture(self):
        """Opens camera connection."""
        try:
            src = self.source
            if isinstance(src, str) and src.strip().isdigit():
                src = int(src.strip())

            if str(src).startswith("rtsp"):
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = f"rtsp_transport;{self.rtsp_transport}"
                cap = cv2.VideoCapture(src, cv2.CAP_FFMPEG)
            else:
                # DirectShow backend on Windows provides immediate opening without MSMF delays
                backend = cv2.CAP_DSHOW if (os.name == 'nt' and isinstance(src, int)) else cv2.CAP_ANY
                cap = cv2.VideoCapture(src, backend)

            # Reduce internal hardware buffer to 1 frame to eliminate latency
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    self.is_connected = True
                    self.status_message = "Camera Connected (Live)"
                    return cap
            
            if cap:
                cap.release()
            return None
        except Exception as e:
            self.status_message = f"Connection error: {str(e)}"
            return None

    def _capture_loop(self):
        """Continuous frame grab loop."""
        frame_counter = 0
        fps_timer = time.time()

        while self.running:
            if self.cap is None or not self.cap.isOpened() or not self.is_connected:
                self.status_message = f"Connecting: {self.source}"
                self.cap = self._open_capture()
                if not self.is_connected:
                    time.sleep(2)
                    continue

            grabbed = self.cap.grab()
            if not grabbed:
                self.is_connected = False
                self.status_message = "Stream interrupted, reconnecting..."
                if self.cap:
                    self.cap.release()
                    self.cap = None
                time.sleep(1)
                continue

            ret, frame = self.cap.retrieve()
            if ret and frame is not None:
                now = time.time()
                with self.lock:
                    self.latest_frame = frame
                    self.last_frame_time = now
                    self.is_connected = True
                    self.status_message = "Live Stream Active"

                frame_counter += 1
                if now - fps_timer >= 1.0:
                    self.fps = frame_counter / (now - fps_timer)
                    frame_counter = 0
                    fps_timer = now
            else:
                self.is_connected = False
                time.sleep(0.5)

    def get_frame(self):
        """Returns the most recent frame."""
        with self.lock:
            if self.latest_frame is not None and (time.time() - self.last_frame_time < 3.0):
                return self.latest_frame.copy(), True
            else:
                return self._create_placeholder_frame(), False

    def _create_placeholder_frame(self):
        """Generates a placeholder image when camera is offline."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (30, 30, 35)

        cv2.putText(frame, "AWAITING CAMERA STREAM", (100, 200),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 215, 255), 2, cv2.LINE_AA)
        
        info = f"Source: {str(self.source)}"
        if len(info) > 45:
            info = info[:45] + "..."
        cv2.putText(frame, info, (100, 245),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)

        status = f"Status: {self.status_message}"
        cv2.putText(frame, status, (100, 280),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (100, 180, 255), 1, cv2.LINE_AA)

        tip = "Configure RTSP connection in Settings."
        cv2.putText(frame, tip, (100, 330),
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
