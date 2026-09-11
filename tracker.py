import cv2
import numpy as np
import time
from collections import defaultdict, deque

class PersonTracker:
    """
    Core AI vision module for person tracking via YOLOv8 and ByteTrack.
    Supports Dual-Zone (Men's Restroom & Women's Restroom) with Dual-Line (Line A & Line B)
    direction-aware tripwires:
      - Line A (Outer) -> Line B (Inner) = ENTRY (GİRİŞ)
      - Line B (Inner) -> Line A (Outer) = EXIT (ÇIKIŞ)
    Also computes adult/child height classification and real-time venue revenue.
    """
    def __init__(self, config, on_event_callback=None):
        self.config = config
        self.on_event_callback = on_event_callback
        self.model = None
        self.is_model_loaded = False

        # Trajectory history and tracking state
        self.track_history = defaultdict(lambda: deque(maxlen=30))
        self.track_heights = defaultdict(list)

        # Dual-line state per track_id: track_id -> zone -> ('A'|'B', timestamp)
        self.zone_cross_state = defaultdict(dict)
        # Cooldown per track_id to prevent duplicate counts: (track_id, zone) -> expiry_time
        self.event_cooldown = {}
        # Prevent rapid repeat trigger on the same line: (track_id, zone, line) -> timestamp
        self.last_line_hit = {}

        # Visual flash state: zone -> (event_type, timestamp)
        self.last_event_flash = {}

        # Stats cache for HUD rendering
        self.stats = {
            "total_count": 0,
            "total_out": 0,
            "total_inside": 0,
            "total_revenue": 0.0,
            "men": {"in": 0, "out": 0, "inside": 0},
            "women": {"in": 0, "out": 0, "inside": 0}
        }

        # Backwards compatibility sets
        self.counted_in_ids = set()
        self.counted_out_ids = set()

        self._load_model()

    def _load_model(self):
        """Loads the YOLOv8 neural network model."""
        try:
            from ultralytics import YOLO
            self.model = YOLO("yolov8n.pt")
            self.is_model_loaded = True
            print("YOLOv8 model loaded successfully.")
        except Exception as e:
            print(f"YOLOv8 load error: {e}")
            self.is_model_loaded = False

    def update_config(self, new_config):
        self.config = new_config

    def set_counts(self, stats):
        """Synchronizes counter stats from the database."""
        self.stats = stats

    @staticmethod
    def _ccw(A, B, C):
        """Tests whether three points are in counter-clockwise order."""
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

    @classmethod
    def _intersect(cls, A, B, C, D):
        """Returns True if line segments AB and CD intersect."""
        return (cls._ccw(A, C, D) != cls._ccw(B, C, D)) and (cls._ccw(A, B, C) != cls._ccw(A, B, D))

    def _get_pixel_line(self, line_dict, w_img, h_img):
        """Converts normalized (0.0-1.0) coordinates to pixel points."""
        p1 = (int(line_dict.get("x1", 0.1) * w_img), int(line_dict.get("y1", 0.5) * h_img))
        p2 = (int(line_dict.get("x2", 0.9) * w_img), int(line_dict.get("y2", 0.5) * h_img))
        return p1, p2

    def process_frame(self, frame):
        """
        Processes a single camera video frame:
        - Detects people and tracks persistent IDs
        - Evaluates Line A / Line B crossings for Men & Women zones
        - Classifies adult vs. child based on bounding box height
        - Draws visual overlays (bounding boxes, tripwires, HUD banner)
        """
        if not self.is_model_loaded or self.model is None:
            return frame, []

        h_img, w_img = frame.shape[:2]
        now = time.time()

        child_threshold = self.config.get("child_height_threshold", 160)
        conf = self.config.get("model_confidence", 0.35)

        # Parse zones (Single line per door with directional normal vector)
        zones_cfg = self.config.get("zones", {})
        parsed_zones = {}
        for zk in ["men", "women"]:
            zdata = zones_cfg.get(zk, {})
            if zdata.get("enabled", True):
                line_data = zdata.get("line")
                if not line_data:
                    # Backward compatibility for old line_a / line_b format
                    la = zdata.get("line_a", {})
                    lb = zdata.get("line_b", {})
                    line_data = {
                        "x1": la.get("x1", 0.1),
                        "y1": (la.get("y1", 0.5) + lb.get("y1", 0.5)) / 2.0,
                        "x2": la.get("x2", 0.4),
                        "y2": (la.get("y2", 0.5) + lb.get("y2", 0.5)) / 2.0,
                    }

                p1 = (int(line_data.get("x1", 0.1) * w_img), int(line_data.get("y1", 0.5) * h_img))
                p2 = (int(line_data.get("x2", 0.4) * w_img), int(line_data.get("y2", 0.5) * h_img))
                entry_dir = int(zdata.get("entry_dir", 1))

                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                nx = -dy * entry_dir
                ny = dx * entry_dir
                norm_len = (nx * nx + ny * ny) ** 0.5
                unx = nx / norm_len if norm_len > 0 else 0.0
                uny = ny / norm_len if norm_len > 0 else 1.0

                parsed_zones[zk] = {
                    "name": zdata.get("name", zk.capitalize()),
                    "p1": p1,
                    "p2": p2,
                    "entry_dir": entry_dir,
                    "normal": (nx, ny),
                    "unit_normal": (unx, uny)
                }

        # Fallback single line if zones not configured
        use_fallback_single = len(parsed_zones) == 0
        if use_fallback_single:
            line_cfg = self.config.get("line_coords", {"x1": 0.1, "y1": 0.5, "x2": 0.9, "y2": 0.5})
            fallback_p1 = (int(line_cfg.get("x1", 0.1) * w_img), int(line_cfg.get("y1", 0.5) * h_img))
            fallback_p2 = (int(line_cfg.get("x2", 0.9) * w_img), int(line_cfg.get("y2", 0.5) * h_img))

        # YOLOv8 Tracking: Person class only (class 0)
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
            return frame, []

        detections = []

        if results and len(results) > 0 and results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.int().cpu().numpy()
            confidences = results[0].boxes.conf.cpu().numpy()

            for box, track_id, score in zip(boxes, track_ids, confidences):
                x1, y1, x2, y2 = box
                box_w = x2 - x1
                box_h = y2 - y1

                # For overhead / ceiling cameras, torso/center point is most reliable
                body_point = (int((x1 + x2) / 2), int(y1 * 0.45 + y2 * 0.55))

                # Height smoothing for Adult/Child classification
                self.track_heights[track_id].append(box_h)
                if len(self.track_heights[track_id]) > 10:
                    self.track_heights[track_id].pop(0)
                avg_h = sum(self.track_heights[track_id]) / len(self.track_heights[track_id])

                # Adult / Child Classification
                is_child = avg_h < child_threshold
                person_type = "child" if is_child else "adult"
                person_label = "Child" if is_child else "Adult"

                detections.append({
                    "track_id": int(track_id),
                    "box": [float(x1), float(y1), float(x2), float(y2)],
                    "type": person_type,
                    "confidence": float(score)
                })

                history = self.track_history[track_id]
                history.append(body_point)

                # Crossing detection
                if len(history) >= 2:
                    curr_pt = history[-1]
                    prev_pt = history[-2]

                    if not use_fallback_single:
                        for zk, zinfo in parsed_zones.items():
                            cd_key = (int(track_id), zk)
                            if self.event_cooldown.get(cd_key, 0) > now:
                                continue

                            p1 = zinfo["p1"]
                            p2 = zinfo["p2"]

                            # Check trajectory segment intersection with door line
                            crossed = self._intersect(prev_pt, curr_pt, p1, p2)
                            if not crossed and len(history) >= 3:
                                crossed = self._intersect(history[-3], curr_pt, p1, p2)
                            if not crossed and len(history) >= 4:
                                crossed = self._intersect(history[-4], curr_pt, p1, p2)

                            if crossed:
                                # Determine motion direction vector using smoothed recent trajectory
                                start_idx = max(0, len(history) - 5)
                                ref_pt = history[start_idx]
                                vx = curr_pt[0] - ref_pt[0]
                                vy = curr_pt[1] - ref_pt[1]

                                if (vx * vx + vy * vy) < 4:
                                    vx = curr_pt[0] - prev_pt[0]
                                    vy = curr_pt[1] - prev_pt[1]

                                unx, uny = zinfo["unit_normal"]
                                dot = vx * unx + vy * uny

                                # Filter out sideways scraping movement
                                if abs(dot) > 0.4:
                                    event_type = "in" if dot > 0 else "out"
                                    # 2.5s cooldown prevents duplicate counting during threshold crossing
                                    self.event_cooldown[cd_key] = now + 2.5
                                    self.last_event_flash[zk] = (event_type, now)

                                    if self.on_event_callback:
                                        self.on_event_callback(zk, event_type, person_type, int(track_id))
                    else:
                        # Fallback single line logic
                        if track_id not in self.counted_in_ids:
                            if self._intersect(prev_pt, curr_pt, fallback_p1, fallback_p2):
                                self.counted_in_ids.add(track_id)
                                self.last_event_flash["general"] = ('in', now)
                                if self.on_event_callback:
                                    self.on_event_callback("men", "in", person_type, int(track_id))

                # Visual bounding box rendering
                box_color = (0, 165, 255) if is_child else (255, 150, 0)
                cd_active = any(self.event_cooldown.get((int(track_id), zk), 0) > now for zk in ["men", "women"])
                if cd_active:
                    box_color = (0, 255, 0)

                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), box_color, 2)

                label_text = f"{person_label} #{track_id}"
                (lw, lh), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(frame, (int(x1), int(y1) - 20), (int(x1) + lw + 6, int(y1)), box_color, -1)
                cv2.putText(frame, label_text, (int(x1) + 3, int(y1) - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

                if len(history) > 1:
                    pts = np.array(history, np.int32).reshape((-1, 1, 2))
                    cv2.polylines(frame, [pts], False, box_color, 2)

        # -----------------------------------------------------------------
        # RENDER SINGLE TRIPWIRE LINE PER DOOR WITH ENTRY ARROW
        # -----------------------------------------------------------------
        if not use_fallback_single:
            line_styles = {
                "men": {
                    "color": (255, 210, 80),   # Sky Blue (BGR)
                    "label": "ERKEK KAPISI"
                },
                "women": {
                    "color": (200, 120, 255),  # Soft Pink (BGR)
                    "label": "KADIN KAPISI"
                }
            }

            for zk, zinfo in parsed_zones.items():
                style = line_styles.get(zk, {"color": (0, 255, 255), "label": zk.upper()})
                color = style["color"]
                flash_text = None

                flash = self.last_event_flash.get(zk)
                if flash and (now - flash[1]) < 1.2:
                    if flash[0] == 'in':
                        color = (0, 255, 0)         # Bright Green for IN
                        flash_text = "+1 GIRIS"
                    else:
                        color = (0, 165, 255)       # Orange for OUT
                        flash_text = "+1 CIKIS"

                p1 = zinfo["p1"]
                p2 = zinfo["p2"]
                unx, uny = zinfo["unit_normal"]

                # 1. Door tripwire line
                cv2.line(frame, p1, p2, color, 3, cv2.LINE_AA)
                cv2.circle(frame, p1, 5, color, -1, cv2.LINE_AA)
                cv2.circle(frame, p2, 5, color, -1, cv2.LINE_AA)

                # 2. Door midpoint
                mid_x = (p1[0] + p2[0]) // 2
                mid_y = (p1[1] + p2[1]) // 2
                mid = (mid_x, mid_y)

                # 3. Direction arrow (Entry arrow pointing inside)
                arrow_len = 36
                arrow_end = (int(mid_x + unx * arrow_len), int(mid_y + uny * arrow_len))
                cv2.arrowedLine(frame, mid, arrow_end, color, 2, tipLength=0.35)

                # 4. Text labels
                label_x = min(p1[0], p2[0]) + 5
                label_y = min(p1[1], p2[1]) - 10
                cv2.putText(frame, style["label"], (label_x, max(label_y, 25)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.48, color, 2, cv2.LINE_AA)

                arrow_text_x = int(mid_x + unx * (arrow_len + 12))
                arrow_text_y = int(mid_y + uny * (arrow_len + 12))
                cv2.putText(frame, "GIRIS", (arrow_text_x - 18, arrow_text_y + 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.40, color, 1, cv2.LINE_AA)

                if flash_text:
                    cv2.putText(frame, flash_text, (mid_x - 30, mid_y - 12),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2, cv2.LINE_AA)
        else:
            fcolor = (0, 255, 255)
            flash = self.last_event_flash.get("general")
            if flash and (now - flash[1]) < 0.8:
                fcolor = (0, 255, 0)
            cv2.line(frame, fallback_p1, fallback_p2, fcolor, 3)

        # -----------------------------------------------------------------
        # TOP HEADS-UP DISPLAY (HUD BANNER)
        # -----------------------------------------------------------------
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w_img, 45), (15, 23, 42), -1)
        cv2.addWeighted(overlay, 0.82, frame, 0.18, 0, frame)

        men_stats = self.stats.get("men", {})
        women_stats = self.stats.get("women", {})
        tot_rev = self.stats.get("total_revenue", 0.0)

        # Men stats HUD
        men_text = f"ERKEK: Giris {men_stats.get('in', 0)} | Cikis {men_stats.get('out', 0)} | Dolu {men_stats.get('inside', 0)}"
        cv2.putText(frame, men_text, (15, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 210, 80), 2, cv2.LINE_AA)

        # Women stats HUD
        women_text = f"KADIN: Giris {women_stats.get('in', 0)} | Cikis {women_stats.get('out', 0)} | Dolu {women_stats.get('inside', 0)}"
        w_offset = max(270, int(w_img * 0.38))
        cv2.putText(frame, women_text, (w_offset, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (200, 130, 255), 2, cv2.LINE_AA)

        # Total revenue HUD
        rev_text = f"KASA: TL {int(tot_rev)}"
        r_offset = max(560, int(w_img * 0.76))
        cv2.putText(frame, rev_text, (r_offset, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (16, 185, 129), 2, cv2.LINE_AA)

        return frame, detections
