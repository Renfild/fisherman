import tempfile
import time
from pathlib import Path

import cv2
import numpy as np

from .audio import AudioMonitor
from .capture import Grabber
from .config import Settings
from .reel import ReelController
from .vision import BobberTracker, GreenZoneDetector, load_template

FAILED = []


def _check(name, condition, detail=""):
    if condition:
        print(f"  ok    {name} {detail}")
    else:
        FAILED.append(name)
        print(f"  FAIL  {name} {detail}")


def _warn(name, condition, detail=""):
    prefix = "ok" if condition else "warn"
    print(f"  {prefix:<4}  {name} {detail}")


def run(settings, logger, base):
    base = Path(base)
    print("Fisherman self-test")
    print("-" * 60)

    print("config")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "settings.ini"
        path.write_text(
            "[Settings]\n"
            "volume_threshold = 5000\n"
            "detection_threshold = 0.55\n"
            "coords = [(1683, 235), (1707, 222)]\n"
            "bait_step1 = None\n"
            "screen_area = {'left': 1362, 'top': 649, 'width': 815, 'height': 240}\n",
            encoding="utf-8",
        )
        loaded = Settings(path)
        _check("old settings.ini parsed",
               loaded.coords() == [(1683, 235), (1707, 222)] and loaded.area()["width"] == 815,
               f"{loaded.coords()} {loaded.area()}")
        loaded.add_spot(10, 20)
        loaded.save()
        again = Settings(path)
        _check("save/load roundtrip",
               again.coords()[-1] == (10, 20) and again["volume_threshold"] == 5000)

    print("vision")
    template = load_template(base / "bobber.png")
    _check("template loaded", template.shape[0] > 10 and template.shape[1] > 10, str(template.shape))

    bar = np.full((90, 900, 3), 32, np.uint8)
    cv2.rectangle(bar, (200, 16), (360, 66), (60, 190, 80), -1)
    height, width = template.shape[:2]
    bar[10:10 + height, 600:600 + width] = template

    zone = GreenZoneDetector().detect(bar)
    _check("green zone detected",
           zone is not None and abs(zone.x0 - 200) <= 8 and abs(zone.x1 - 360) <= 8,
           "" if zone is None else f"{zone.x0}-{zone.x1}")

    tracker = BobberTracker(template, threshold=0.5)
    match = tracker.detect(bar)
    _check("bobber found",
           match is not None and abs(match.cx - (600 + width / 2)) <= 10,
           "" if match is None else f"x={match.cx:.0f} score={match.score:.2f}")

    bar2 = bar.copy()
    bar2[10:10 + height, 600:600 + width] = (32, 32, 32)
    bar2[10:10 + height, 255:255 + width] = template
    tracker.reset()
    band = (zone.y0 - 45, zone.y1 + 45) if zone else None
    match2 = tracker.detect(bar2, band=band)
    _check("bobber over green zone",
           match2 is not None and abs(match2.cx - (255 + width / 2)) <= 10,
           "" if match2 is None else f"x={match2.cx:.0f}")

    print("controller")
    controller = ReelController(deadband=6.0, lead=0.08, hold_right=True)
    position, velocity, holding, now, target = 80.0, 0.0, False, 0.0, 380.0
    worst = 0.0
    for index in range(900):
        target_velocity = 260.0 if holding else -130.0
        velocity += (target_velocity - velocity) * min(1.0, 0.011 * 12.0)
        position = min(760.0, max(20.0, position + velocity * 0.011))
        holding = controller.decide(position, target, now, holding)
        now += 0.011
        if index > 300:
            worst = max(worst, abs(position - target))
    _check("reel controller keeps target", worst <= 45.0, f"worst deviation {worst:.1f}px")

    print("capture")
    try:
        grabber = Grabber()
        frame = grabber.grab({"left": 60, "top": 60, "width": 240, "height": 160})
        grabber.close()
        _check("screen capture", frame.shape == (160, 240, 3), str(frame.shape))
    except Exception as error:
        _check("screen capture", False, repr(error))

    print("audio")
    monitor = AudioMonitor(threshold=10 ** 9, ratio=100.0, source="auto")
    monitor.start()
    time.sleep(1.0)
    backend = monitor.backend
    level = monitor.level
    monitor.stop()
    monitor.join(timeout=2.0)
    _warn("audio backend", backend is not None, f"{backend}, level {level}")

    print("-" * 60)
    if FAILED:
        print(f"FAILED: {len(FAILED)} -> {', '.join(FAILED)}")
        return 1
    print("All core checks passed")
    return 0
