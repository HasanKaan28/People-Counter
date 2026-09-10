import cv2
import numpy as np
import time
from collections import defaultdict, deque
import math

class PersonTracker:
    """
    YOLOv8 ve ByteTrack ile kişi takibi, sanal çizgi (tripwire) geçiş tespiti,
    yetişkin / çocuk ayrımı ve ciro hesabı yapan çekirdek yapay zeka modülü.
    """
    def __init__(self, config, on_entrance_callback=None):
        self.config = config
        self.on_entrance_callback = on_entrance_callback
        self.model = None
        self.is_model_loaded = False

        # Takip geçmişi ve durumlar
        self.track_history = defaultdict(lambda: deque(maxlen=30))
        self.track_heights = defaultdict(list)
        self.counted_in_ids = set()
        self.counted_out_ids = set()
        self.last_cross_time = 0
        self.recent_cross_color = (0, 255, 255)

        # Yerel anlık sayaçlar (Veri tabanı ile senkronize)
        self.today_adults = 0
        self.today_children = 0
        self.today_total = 0
        self.today_revenue = 0.0

        # Başlangıçta modeli yükle
        self._load_model()

    def _load_model(self):
        """YOLOv8 modelini yukler."""
        try:
            from ultralytics import YOLO
            # yolov8n.pt hem cok hafif hem de 13 saatlik CPU/GPU kullaniminda cok az kaynak harcar
            self.model = YOLO("yolov8n.pt")
            self.is_model_loaded = True
            print("YOLOv8 Modeli basariyla yuklendi.")
        except Exception as e:
            print(f"YOLOv8 yukleme hatasi: {e}")
            self.is_model_loaded = False

    def update_config(self, new_config):
        self.config = new_config

    def set_counts(self, stats):
        """Veri tabanından gelen güncel sayıları senkronize eder."""
        self.today_adults = stats.get("adult_count", 0)
        self.today_children = stats.get("child_count", 0)
        self.today_total = stats.get("total_count", 0)
        self.today_revenue = stats.get("total_revenue", 0.0)

    @staticmethod
    def _ccw(A, B, C):
        """Üç noktanın saat yönünün tersi olup olmadığını test eder."""
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

    @classmethod
    def _intersect(cls, A, B, C, D):
        """AB ve CD doğru parçalarının kesişip kesişmediğini döndürür."""
        return (cls._ccw(A, C, D) != cls._ccw(B, C, D)) and (cls._ccw(A, B, C) != cls._ccw(A, B, D))

    @staticmethod
    def _get_side(line_p1, line_p2, pt):
        """Bir noktanın çizginin hangi tarafında olduğunu vektörel çarpımla belirler."""
        x1, y1 = line_p1
        x2, y2 = line_p2
        px, py = pt
        return (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)

    def process_frame(self, frame):
        """
        Kamera karesini işler:
        - İnsanları tespit eder ve takip ID'lerini çıkarır
        - Çizgi geçişlerini ve yönünü yakalar
        - Yetişkin / Çocuk ayrımını yapar
        - Kare üzerine görsel göstergeleri (bounding box, çizgi, sayaç) çizer.
        """
        if not self.is_model_loaded or self.model is None:
            # Model henüz hazır değilse sadece kareyi döndür
            return frame, []

        h_img, w_img = frame.shape[:2]

        # Çizgi koordinatlarını piksele dönüştür
        line_cfg = self.config.get("line_coords", {"x1": 0.1, "y1": 0.5, "x2": 0.9, "y2": 0.5})
        p1 = (int(line_cfg.get("x1", 0.1) * w_img), int(line_cfg.get("y1", 0.5) * h_img))
        p2 = (int(line_cfg.get("x2", 0.9) * w_img), int(line_cfg.get("y2", 0.5) * h_img))

        child_threshold = self.config.get("child_height_threshold", 160)
        conf = self.config.get("model_confidence", 0.35)
        in_direction = self.config.get("in_direction", "down")

        # YOLOv8 Takip: Sadece insan sınıfı (class 0)
        try:
            results = self.model.track(
                frame,
                persist=True,
                tracker="bytetrack.yaml",
                classes=[0],
                conf=conf,
                verbose=False
            )
        except Exception as e:
            # Takip hatası olursa kareyi olduğu gibi döndür
            return frame, []

        detections = []
        now = time.time()

        if results and len(results) > 0 and results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.int().cpu().numpy()
            confidences = results[0].boxes.conf.cpu().numpy()

            for box, track_id, score in zip(boxes, track_ids, confidences):
                x1, y1, x2, y2 = box
                box_w = x2 - x1
                box_h = y2 - y1

                # Kişinin ayak / yer temas noktası (Kapı eşiğini en doğru ayak noktası belirler)
                foot_point = (int((x1 + x2) / 2), int(y2))

                # Boyut geçmişi
                self.track_heights[track_id].append(box_h)
                if len(self.track_heights[track_id]) > 10:
                    self.track_heights[track_id].pop(0)
                avg_h = sum(self.track_heights[track_id]) / len(self.track_heights[track_id])

                # Yetişkin / Çocuk Sınıflandırması
                is_child = avg_h < child_threshold
                person_type = "child" if is_child else "adult"
                person_label = "Cocuk" if is_child else "Yetiskin"

                detections.append({
                    "track_id": int(track_id),
                    "box": [float(x1), float(y1), float(x2), float(y2)],
                    "type": person_type,
                    "confidence": float(score)
                })

                # Hareket geçmişi
                history = self.track_history[track_id]
                history.append(foot_point)

                # Çizgi Kesişim ve Geçiş Kontrolü
                if len(history) >= 2 and track_id not in self.counted_in_ids:
                    prev_pt = history[-2]
                    curr_pt = history[-1]

                    # Doğru parçaları kesişiyor mu?
                    if self._intersect(prev_pt, curr_pt, p1, p2):
                        # Yön hesabı
                        # Çizginin bir tarafından diğer tarafına geçiş
                        side_prev = self._get_side(p1, p2, prev_pt)
                        side_curr = self._get_side(p1, p2, curr_pt)

                        # Yön belirleme:
                        # Eğer yatay bir çizgi ve "down" yönü ise: y değerinin artması içeri giriştir.
                        # Genel vektörel kontrol:
                        is_in = False
                        if in_direction == "down":
                            is_in = (curr_pt[1] > prev_pt[1])
                        elif in_direction == "up":
                            is_in = (curr_pt[1] < prev_pt[1])
                        elif in_direction == "right":
                            is_in = (curr_pt[0] > prev_pt[0])
                        elif in_direction == "left":
                            is_in = (curr_pt[0] < prev_pt[0])
                        else:
                            is_in = (side_prev < 0 and side_curr >= 0)

                        if is_in:
                            self.counted_in_ids.add(track_id)
                            self.last_cross_time = now
                            self.recent_cross_color = (0, 255, 0)

                            # Giriş olayını tetikle
                            if self.on_entrance_callback:
                                self.on_entrance_callback(person_type, int(track_id))

                # Kutu ve Etiket Çizimi
                # Yetişkin için Mavi/Yeşil, Çocuk için Turuncu/Sarı
                box_color = (0, 165, 255) if is_child else (255, 150, 0)
                if track_id in self.counted_in_ids:
                    box_color = (0, 255, 0)  # Girenler yeşil kutu olur

                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), box_color, 2)
                
                # Etiket zemini
                label_text = f"{person_label} #{track_id}"
                (lw, lh), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(frame, (int(x1), int(y1) - 20), (int(x1) + lw + 6, int(y1)), box_color, -1)
                cv2.putText(frame, label_text, (int(x1) + 3, int(y1) - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

                # İz / Yörünge çizgisi
                if len(history) > 1:
                    pts = np.array(history, np.int32).reshape((-1, 1, 2))
                    cv2.polylines(frame, [pts], False, box_color, 2)

        # Sanal Çizgiyi (Tripwire) Çiz
        line_color = (0, 255, 255)  # Sarı
        if now - self.last_cross_time < 0.8:
            line_color = (0, 255, 0)  # Geçiş olduğunda anlık yeşil parlar

        cv2.line(frame, p1, p2, line_color, 3)
        cv2.circle(frame, p1, 6, (0, 0, 255), -1)
        cv2.circle(frame, p2, 6, (0, 0, 255), -1)

        # Çizgi üzerine yön oku ve yazı ekle
        mid_x = int((p1[0] + p2[0]) / 2)
        mid_y = int((p1[1] + p2[1]) / 2)
        direction_text = f"GIRIS ({in_direction.upper()})"
        cv2.putText(frame, direction_text, (mid_x - 40, mid_y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, line_color, 2, cv2.LINE_AA)

        # Üst Bilgi Başlığı (Canlı Sayaç Bandı)
        # Yarı saydam siyah şerit
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w_img, 42), (20, 20, 25), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        stats_banner = f"GIRIS: {self.today_total}  |  YETISKIN: {self.today_adults}  |  COCUK: {self.today_children}  |  KASA: {int(self.today_revenue)} TL"
        cv2.putText(frame, stats_banner, (15, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)

        return frame, detections
