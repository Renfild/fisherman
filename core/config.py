import ast
import configparser
from pathlib import Path


DEFAULTS = {
    "game_window": "Albion Online",

    "coords": [],
    "bait_step1": None,
    "bait_step2": None,
    "move_spot": None,
    "screen_area": {"left": 0, "top": 0, "width": 0, "height": 0},

    "volume_threshold": 3000,
    "audio_ratio": 2.2,
    "audio_source": "auto",
    "ignore_after_cast": 3.0,
    "hook_delay": 0.4,

    "detection_threshold": 0.5,
    "use_green_zone": True,
    "hold_dir": "right",
    "green_hsv_low": (35, 50, 40),
    "green_hsv_high": (90, 255, 255),
    "reel_deadband": 6.0,
    "reel_lead": 0.08,

    "bite_timeout": 22.0,
    "reel_timeout": 16.0,
    "post_delay": (1.0, 1.8),
    "cast_hold": (0.8, 1.2),
    "cast_move_time": 0.35,

    "food_key": "2",
    "food_interval": 1800.0,
    "bait_interval": 600.0,
    "move_interval": 300.0,

    "require_focus": True,
    "debug": False,
}


class Settings:
    def __init__(self, path):
        self.path = Path(path)
        self.data = dict(DEFAULTS)
        self.load()

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def get(self, key, default=None):
        return self.data.get(key, default)

    def load(self):
        if not self.path.exists():
            return
        parser = configparser.ConfigParser()
        try:
            parser.read(self.path, encoding="utf-8")
        except configparser.Error:
            return
        if not parser.has_section("Settings"):
            return
        for key, raw in parser["Settings"].items():
            self.data[key] = self._coerce(key, raw)
        self._normalize()

    def save(self):
        parser = configparser.ConfigParser()
        parser["Settings"] = {key: str(value) for key, value in self.data.items()}
        with self.path.open("w", encoding="utf-8") as handle:
            parser.write(handle)

    def coords(self):
        result = []
        for item in self.data.get("coords") or []:
            try:
                result.append((int(item[0]), int(item[1])))
            except (TypeError, ValueError, IndexError):
                continue
        return result

    def add_spot(self, x, y):
        spots = self.coords()
        spots.append((int(x), int(y)))
        self.data["coords"] = spots

    def clear_spots(self):
        self.data["coords"] = []

    def set_point(self, key, point):
        self.data[key] = None if point is None else (int(point[0]), int(point[1]))

    def point(self, key):
        value = self.data.get(key)
        if isinstance(value, (list, tuple)) and len(value) == 2:
            return int(value[0]), int(value[1])
        return None

    def area(self):
        raw = self.data.get("screen_area") or {}
        return {key: int(raw.get(key, 0)) for key in ("left", "top", "width", "height")}

    def set_area(self, left, top, width, height):
        self.data["screen_area"] = {
            "left": int(left),
            "top": int(top),
            "width": int(width),
            "height": int(height),
        }

    def problems(self):
        issues = []
        if not self.coords():
            issues.append("no fishing spots set")
        area = self.area()
        if area["width"] < 60 or area["height"] < 20:
            issues.append("tracking zone is not set")
        threshold = self.data.get("volume_threshold", 0)
        if not isinstance(threshold, int) or threshold < 100:
            issues.append("volume threshold looks invalid")
        detection = self.data.get("detection_threshold", 0)
        if not isinstance(detection, (int, float)) or not 0.1 <= float(detection) <= 0.99:
            issues.append("detection threshold must be between 0.1 and 0.99")
        return issues

    @staticmethod
    def _literal(raw):
        try:
            return ast.literal_eval(raw.strip())
        except (ValueError, SyntaxError):
            return raw.strip()

    def _coerce(self, key, raw):
        value = self._literal(raw)
        default = DEFAULTS.get(key)
        try:
            if isinstance(default, bool):
                return bool(value)
            if isinstance(default, int):
                return int(value)
            if isinstance(default, float):
                return float(value)
            if isinstance(default, str):
                return str(value)
            if isinstance(default, tuple):
                if all(isinstance(part, int) for part in default):
                    return tuple(int(part) for part in value)
                return tuple(float(part) for part in value)
            if isinstance(default, list):
                return list(value)
            if isinstance(default, dict) and isinstance(value, dict):
                merged = dict(default)
                merged.update(value)
                return merged
        except (TypeError, ValueError):
            pass
        return default if default is not None else value

    def _normalize(self):
        self.data["coords"] = self.coords()
        self.data["screen_area"] = self.area()
        for key in ("bait_step1", "bait_step2", "move_spot"):
            self.data[key] = self.point(key)
        for key in ("post_delay", "cast_hold"):
            value = self.data.get(key)
            if not (isinstance(value, tuple) and len(value) == 2):
                self.data[key] = DEFAULTS[key]
        if self.data.get("hold_dir") not in ("right", "left"):
            self.data["hold_dir"] = "right"
        if self.data.get("audio_source") not in ("auto", "loopback", "input"):
            self.data["audio_source"] = "auto"
