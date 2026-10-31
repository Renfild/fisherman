import cv2
import mss
import numpy as np


class Grabber:
    def __init__(self):
        self._sct = mss.mss()

    def grab(self, area):
        region = {key: int(area[key]) for key in ("left", "top", "width", "height")}
        raw = np.asarray(self._sct.grab(region))
        return cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)

    def close(self):
        try:
            self._sct.close()
        except Exception:
            pass
