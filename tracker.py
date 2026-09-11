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

        # Parse zones
        zones_cfg = self.config.get("zones", {})
        parsed_zones = {}
        for zk in ["men", "women"]:
            zdata = zones_cfg.get(zk, {})
            if zdata.get("enabled", True):
                la = zdata.get("line_a", {})
                lb = zdata.get("line_b", {})
                parsed_zones[zk] = {
                    "name": zdata.get("name", zk.capitalize()),
                    "p1_a": (int(la.get("x1", 0.1) * w_img), int(la.get("y1", 0.4) * h_img)),
                    "p2_a": (int(la.get("x2", 0.4) * w_img), int(la.get("y2", 0.4) * h_img)),
                    "p1_b": (int(lb.get("x1", 0.1) * w_img), int(lb.get("y1", 0.6) * h_img)),
                    "p2_b": (int(lb.get("x2", 0.4) * w_img), int(lb.get("y2", 0.6) * h_img)),
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

                # Ground contact / foot position
                foot_point = (int((x1 + x2) / 2), int(y2))

                # Height smoothing
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
                history.append(foot_point)

                # Need at least 2 points to check intersection
                if len(history) >= 2:
                    prev_pt = history[-2]
                    curr_pt = history[-1]

                    if not use_fallback_single:
                        # Process dual lines for each zone (Men / Women)
                        for zk, zinfo in parsed_zones.items():
                            cd_key = (int(track_id), zk)
                            if self.event_cooldown.get(cd_key, 0) > now:
                                continue

                            # Check Line A intersection
                            hit_a = self._intersect(prev_pt, curr_pt, zinfo["p1_a"], zinfo["p2_a"])
                            # Check Line B intersection
                            hit_b = self._intersect(prev_pt, curr_pt, zinfo["p1_b"], zinfo["p2_b"])

                            # Handle Line A hit
                            if hit_a:
                                last_hit_a = self.last_line_hit.get((track_id, zk, 'A'), 0)
                                if now - last_hit_a > 0.6:
                                    self.last_line_hit[(track_id, zk, 'A')] = now
                                    prev_state = self.zone_cross_state[track_id].get(zk)

                                    if prev_state and prev_state[0] == 'B' and (now - prev_state[1]) < 9.0:
                                        # Crossed B then A -> EXIT (ÇIKIŞ)!
                                        self.event_cooldown[cd_key] = now + 3.0
                                        self.zone_cross_state[track_id].pop(zk, None)
                                        self.last_event_flash[zk] = ('out', now)
                                        if self.on_event_callback:
                                            self.on_event_callback(zk, "out", person_type, int(track_id))
                                    else:
                                        # First crossed Line A
                                        self.zone_cross_state[track_id][zk] = ('A', now)

                            # Handle Line B hit
                            if hit_b:
                                last_hit_b = self.last_line_hit.get((track_id, zk, 'B'), 0)
                                if now - last_hit_b > 0.6:
                                    self.last_line_hit[(track_id, zk, 'B')] = now
                                    prev_state = self.zone_cross_state[track_id].get(zk)

                                    if prev_state and prev_state[0] == 'A' and (now - prev_state[1]) < 9.0:
                                        # Crossed A then B -> ENTRY (GİRİŞ)!
                                        self.event_cooldown[cd_key] = now + 3.0
                                        self.zone_cross_state[track_id].pop(zk, None)
                                        self.last_event_flash[zk] = ('in', now)
                                        if self.on_event_callback:
                                            self.on_event_callback(zk, "in", person_type, int(track_id))
                                    else:
                                        # First crossed Line B
                                        self.zone_cross_state[track_id][zk] = ('B', now)
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
        # RENDER DUAL-ZONE TRIPWIRE LINES
        # -----------------------------------------------------------------
        if not use_fallback_single:
            # Color schemes (BGR format):
            # Men: Line A = Light Cyan (255, 210, 80), Line B = Deep Blue (230, 100, 20)
            # Women: Line A = Soft Pink (200, 120, 255), Line B = Purple/Magenta (190, 40, 200)
            line_styles = {
                "men": {
                    "color_a": (255, 210, 80),
                    "color_b": (230, 110, 30),
                    "label": "MEN"
                },
                "women": {
                    "color_a": (200, 120, 255),
                    "color_b": (190, 40, 200),
                    "label": "WOMEN"
                }
            }

            for zk, zinfo in parsed_zones.items():
                style = line_styles.get(zk, {"color_a": (0, 255, 255), "color_b": (255, 255, 0), "label": zk.upper()})
                color_a = style["color_a"]
                color_b = style["color_b"]

                flash = self.last_event_flash.get(zk)
                if flash and (now - flash[1]) < 0.9:
                    if flash[0] == 'in':
                        color_a = color_b = (0, 255, 0)      # Bright Green for IN
                    else:
                        color_a = color_b = (0, 165, 255)    # Orange for OUT

                # Draw Line A (Outer / Dış Çizgi - Kapı Önü)
                p1_a, p2_a = zinfo["p1_a"], zinfo["p2_a"]
                cv2.line(frame, p1_a, p2_a, color_a, 2)
                cv2.circle(frame, p1_a, 5, color_a, -1)
                cv2.circle(frame, p2_a, 5, color_a, -1)
                mid_a = ((p1_a[0] + p2_a[0]) // 2, (p1_a[1] + p2_a[1]) // 2)
                cv2.putText(frame, f"{style['label']} 1 (DIS)", (mid_a[0] - 45, mid_a[1] - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, color_a, 1, cv2.LINE_AA)

                # Draw Line B (Inner / İç Çizgi - Tuvalet İçi)
                p1_b, p2_b = zinfo["p1_b"], zinfo["p2_b"]
                cv2.line(frame, p1_b, p2_b, color_b, 2)
                cv2.circle(frame, p1_b, 5, color_b, -1)
                cv2.circle(frame, p2_b, 5, color_b, -1)
                mid_b = ((p1_b[0] + p2_b[0]) // 2, (p1_b[1] + p2_b[1]) // 2)
                cv2.putText(frame, f"{style['label']} 2 (IC)", (mid_b[0] - 40, mid_b[1] - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, color_b, 1, cv2.LINE_AA)

                # Draw Direction indicator between lines (1 -> 2 = GİRİŞ)
                arrow_start = mid_a
                arrow_end = mid_b
                cv2.arrowedLine(frame, arrow_start, arrow_end, color_b, 1, tipLength=0.25)
        else:
            # Fallback single line render
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
        men_text = f"MEN: In {men_stats.get('in', 0)} | Out {men_stats.get('out', 0)} | Inside {men_stats.get('inside', 0)}"
        cv2.putText(frame, men_text, (15, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 210, 80), 2, cv2.LINE_AA)

        # Women stats HUD
        women_text = f"WOMEN: In {women_stats.get('in', 0)} | Out {women_stats.get('out', 0)} | Inside {women_stats.get('inside', 0)}"
        w_offset = max(280, int(w_img * 0.38))
        cv2.putText(frame, women_text, (w_offset, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 130, 255), 2, cv2.LINE_AA)

        # Total revenue HUD
        rev_text = f"REVENUE: ${int(tot_rev)}"
        r_offset = max(580, int(w_img * 0.76))
        cv2.putText(frame, rev_text, (r_offset, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (16, 185, 129), 2, cv2.LINE_AA)

        return frame, detections
