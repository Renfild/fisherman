import os
import time

import cv2
import numpy as np


def load_template(path):
    path = str(path)
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    data = np.fromfile(path, dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError(f"cannot decode template: {path}")
    if image.ndim == 3 and image.shape[2] == 4:
        alpha = image[:, :, 3]
        ys, xs = np.where(alpha > 8)
        if len(xs):
            image = image[ys.min():ys.max() + 1, xs.min():xs.max() + 1, :3]
        else:
            image = image[:, :, :3]
    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    return np.ascontiguousarray(image[:, :, :3])


class Zone:
    __slots__ = ("x0", "x1", "y0", "y1")

    def __init__(self, x0, x1, y0, y1):
        self.x0 = int(x0)
        self.x1 = int(x1)
        self.y0 = int(y0)
        self.y1 = int(y1)

    @property
    def center(self):
        return (self.x0 + self.x1) / 2.0

    @property
    def width(self):
        return self.x1 - self.x0


class Match:
    __slots__ = ("score", "x", "y", "w", "h", "scale", "index")

    def __init__(self, score, x, y, w, h, scale, index=0):
        self.score = float(score)
        self.x = int(x)
        self.y = int(y)
        self.w = int(w)
        self.h = int(h)
        self.scale = float(scale)
        self.index = int(index)

    @property
    def cx(self):
        return self.x + self.w / 2.0

    @property
    def cy(self):
        return self.y + self.h / 2.0


class GreenZoneDetector:
    def __init__(self, low=(35, 50, 40), high=(90, 255, 255)):
        self.low = np.array(low, dtype=np.uint8)
        self.high = np.array(high, dtype=np.uint8)

    def detect(self, roi):
        if roi is None or roi.size == 0:
            return None
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.low, self.high)
        height, width = mask.shape[:2]
        min_pixels = max(2, int(height * 0.05))
        columns = (mask > 0).sum(axis=0)
        candidates = np.flatnonzero(columns >= min_pixels)
        if candidates.size < 6:
            return None

        runs = []
        start = previous = int(candidates[0])
        for column in candidates[1:]:
            column = int(column)
            if column - previous <= 4:
                previous = column
                continue
            runs.append((start, previous))
            start = previous = column
        runs.append((start, previous))
        x0, x1 = max(runs, key=lambda run: run[1] - run[0])
        if x1 - x0 < 6:
            return None
        if (x1 - x0) > 0.92 * width:
            return None

        rows = np.flatnonzero((mask[:, x0:x1 + 1] > 0).sum(axis=1) > 0)
        if rows.size < 2:
            return None
        return Zone(x0, x1, rows.min(), rows.max())


class BobberTracker:
    def __init__(self, template, threshold=0.5, scales=(0.7, 0.85, 1.0, 1.15, 1.35, 1.6)):
        self.threshold = float(threshold)
        self.templates = []
        for scale in scales:
            resized = cv2.resize(template, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            if resized.shape[0] >= 12 and resized.shape[1] >= 12:
                self.templates.append((resized, scale))
        if not self.templates:
            raise ValueError("template is too small")
        self.last = None
        self._preferred = None

    def reset(self):
        self.last = None
        self._preferred = None

    def detect(self, roi, band=None, now=None):
        if roi is None or roi.size == 0 or not self.templates:
            return None
        now = time.perf_counter() if now is None else now
        height, width = roi.shape[:2]
        if band is None:
            y0, y1 = 0, height
        else:
            y0 = max(0, int(band[0]))
            y1 = min(height, int(band[1]))
        if y1 - y0 < 12:
            y0, y1 = 0, height

        def scan(x_start, x_end):
            crop = roi[y0:y1, x_start:x_end]
            if crop.shape[0] < 12 or crop.shape[1] < 12:
                return None
            crop = np.ascontiguousarray(crop)
            order = list(range(len(self.templates)))
            if self._preferred is not None:
                order.remove(self._preferred)
                order.insert(0, self._preferred)
            best = None
            for index in order:
                template, scale = self.templates[index]
                th, tw = template.shape[:2]
                if th > crop.shape[0] or tw > crop.shape[1]:
                    continue
                result = cv2.matchTemplate(crop, template, cv2.TM_CCOEFF_NORMED)
                _, max_value, _, max_location = cv2.minMaxLoc(result)
                if best is None or max_value > best.score:
                    best = Match(max_value, x_start + max_location[0], y0 + max_location[1], tw, th, scale, index)
                if index == self._preferred and max_value >= self.threshold:
                    break
            return best

        best = None
        if self.last is not None:
            pad = 80
            best = scan(max(0, int(self.last.x - pad)), min(width, int(self.last.x + self.last.w + pad)))
        if best is None or best.score < self.threshold:
            full = scan(0, width)
            if full is not None and (best is None or full.score > best.score):
                best = full
        if best is None or best.score < self.threshold:
            return None
        self._preferred = best.index
        self.last = best
        return best


class BarFrame:
    __slots__ = ("zone", "match", "target_x", "width")

    def __init__(self, zone, match, target_x, width):
        self.zone = zone
        self.match = match
        self.target_x = target_x
        self.width = width

    @property
    def ok(self):
        return self.match is not None


class BarAnalyzer:
    def __init__(self, template, threshold=0.5, use_green_zone=True,
                 green_low=(35, 50, 40), green_high=(90, 255, 255)):
        self.tracker = BobberTracker(template, threshold=threshold)
        self.zone_detector = GreenZoneDetector(green_low, green_high)
        self.use_green_zone = use_green_zone

    def analyze(self, roi, now=None):
        zone = self.zone_detector.detect(roi) if self.use_green_zone else None
        band = None
        if zone is not None:
            band = (zone.y0 - 45, zone.y1 + 45)
        match = self.tracker.detect(roi, band=band, now=now)
        target = zone.center if zone is not None else roi.shape[1] / 2.0
        return BarFrame(zone, match, target, roi.shape[1])

    def draw(self, roi, frame):
        canvas = roi.copy()
        if frame.zone is not None:
            cv2.rectangle(canvas, (frame.zone.x0, frame.zone.y0), (frame.zone.x1, frame.zone.y1), (0, 200, 0), 1)
        if frame.match is not None:
            match = frame.match
            cv2.rectangle(canvas, (match.x, match.y), (match.x + match.w, match.y + match.h), (0, 165, 255), 1)
            cv2.putText(canvas, f"{match.score:.2f}", (match.x, max(12, match.y - 4)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 165, 255), 1, cv2.LINE_AA)
            cv2.line(canvas, (int(match.cx), 0), (int(match.cx), canvas.shape[0] - 1), (0, 165, 255), 1)
        cv2.line(canvas, (int(frame.target_x), 0), (int(frame.target_x), canvas.shape[0] - 1), (255, 0, 255), 1)
        label = "zone: none" if frame.zone is None else f"zone: {frame.zone.x0}-{frame.zone.x1}"
        if frame.match is not None:
            label += f"   score {frame.match.score:.2f}   x {frame.match.cx:.0f}   target {frame.target_x:.0f}"
        cv2.putText(canvas, label, (4, canvas.shape[0] - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
        return canvas
