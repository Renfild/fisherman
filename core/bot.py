import random
import threading
import time
from pathlib import Path

import cv2

from .capture import Grabber
from .input import Input, VK_F8, VK_F9
from .reel import ReelController
from .vision import BarAnalyzer, load_template


class Stopped(Exception):
    pass


class Bot(threading.Thread):
    def __init__(self, settings, audio, logger, base):
        super().__init__(daemon=True, name="bot")
        self.s = settings
        self.audio = audio
        self.log = logger
        self.base = Path(base)
        self.input = Input()

        self.armed = threading.Event()
        self.state = "IDLE"
        self.stats = {"casts": 0, "bites": 0, "reels": 0}

        self._stop_event = threading.Event()
        self._cast_point = None
        self._recover_single = False
        self._f8_prev = False
        self._f9_prev = False
        self._grabber = None
        self._template = None

        self._next_food = 0.0
        self._next_bait = 0.0
        self._next_move = 0.0

    def run(self):
        try:
            self._template = load_template(self.base / "bobber.png")
        except Exception as error:
            self.log(f"Template error: {error}")
            return
        self._grabber = Grabber()
        self.log("Bot thread ready")
        try:
            while not self._stop_event.is_set():
                self._poll_hotkeys()
                if not self.armed.is_set():
                    self._release_mouse()
                    self.state = "IDLE"
                    self._stop_event.wait(0.05)
                    continue
                try:
                    self._cycle()
                except Stopped:
                    self._release_mouse()
                except Exception as error:
                    self.log(f"Cycle error: {error!r}")
                    self._release_mouse()
                    time.sleep(0.5)
        finally:
            self._release_mouse()
            if self._grabber is not None:
                self._grabber.close()

    def status(self):
        return {
            "state": self.state,
            "armed": self.armed.is_set(),
            "casts": self.stats["casts"],
            "bites": self.stats["bites"],
            "reels": self.stats["reels"],
        }

    def start_bot(self):
        issues = self.s.problems()
        for issue in issues:
            self.log(f"Cannot start: {issue}")
        if issues:
            return False
        area = self.s.area()
        screen_w, screen_h = self.input.screen_size()
        if (area["left"] < 0 or area["top"] < 0
                or area["left"] + area["width"] > screen_w
                or area["top"] + area["height"] > screen_h):
            self.log("Cannot start: tracking zone is outside the screen")
            return False
        now = time.perf_counter()
        self.stats = {"casts": 0, "bites": 0, "reels": 0}
        self._next_food = now + 1.0
        self._next_bait = now + 3.0 if self._bait_ready() else float("inf")
        self._next_move = now + float(self.s["move_interval"])
        self._recover_single = False
        if self.s["require_focus"] and not self.input.is_focused(self.s["game_window"]):
            self.input.focus_game(self.s["game_window"])
        self.armed.set()
        self.log("Bot started")
        return True

    def stop_bot(self):
        if self.armed.is_set():
            self.armed.clear()
            self.log("Bot stopped")

    def shutdown(self):
        self.armed.clear()
        self._stop_event.set()

    def _poll_hotkeys(self):
        f8 = self.input.is_down(VK_F8)
        if f8 and not self._f8_prev:
            if self.armed.is_set():
                self.stop_bot()
            else:
                self.start_bot()
        self._f8_prev = f8
        f9 = self.input.is_down(VK_F9)
        if f9 and not self._f9_prev:
            self.stop_bot()
        self._f9_prev = f9

    def _check(self):
        self._poll_hotkeys()
        if self._stop_event.is_set() or not self.armed.is_set():
            raise Stopped
        if self.input.failsafe_tripped():
            self.log("Failsafe: cursor in the top-left corner -> stop")
            self.stop_bot()
            raise Stopped

    def _ensure_focus(self):
        if not self.s["require_focus"]:
            return
        if self.input.is_focused(self.s["game_window"]):
            return
        self.log("Game window lost focus -> stop")
        self.stop_bot()
        raise Stopped

    def _release_mouse(self):
        try:
            self.input.mouse_up()
        except Exception:
            pass

    def _bait_ready(self):
        return bool(self.s.point("bait_step1") and self.s.point("bait_step2"))

    def _cycle(self):
        self._automation()
        self._cast()
        if not self._wait_bite():
            self._recover()
            return
        self._hook()
        self._reel()
        self._post()

    def _automation(self):
        now = time.perf_counter()
        if self.s["food_key"] and now >= self._next_food:
            self._ensure_focus()
            self._check()
            self.input.key_press(str(self.s["food_key"]))
            self.log("Food buff used")
            self._next_food = now + float(self.s["food_interval"])
        if self._bait_ready() and now >= self._next_bait:
            self._apply_bait()
            self._next_bait = now + float(self.s["bait_interval"])
        if self.s["move_spot"] and now >= self._next_move:
            self._ensure_focus()
            self._check()
            point = self.s.point("move_spot")
            self.input.click(point[0], point[1], hold=random.uniform(0.05, 0.1), button="right")
            self.log("Anti-fatigue move")
            self._next_move = now + float(self.s["move_interval"])

    def _apply_bait(self):
        first = self.s.point("bait_step1")
        second = self.s.point("bait_step2")
        if not first or not second:
            return
        self._ensure_focus()
        self._check()
        self.log("Applying bait")
        width, height = self.input.screen_size()
        self.input.click(width // 2, height // 2, hold=0.05)
        time.sleep(0.5)
        self.input.key_press("i")
        time.sleep(1.5)
        self.input.click(first[0], first[1], hold=0.08)
        time.sleep(0.8)
        self.input.click(second[0], second[1], hold=0.08)
        time.sleep(5.5)
        self.input.key_press("i")
        time.sleep(1.0)

    def _cast(self):
        spots = self.s.coords()
        if not spots:
            self.log("No fishing spots configured")
            time.sleep(1.0)
            raise Stopped
        self._ensure_focus()
        self._check()
        base_x, base_y = random.choice(spots)
        x = base_x + random.randint(-5, 5)
        y = base_y + random.randint(-5, 5)
        self.input.move_to(x, y, duration=float(self.s["cast_move_time"]))
        hold_min, hold_max = self.s["cast_hold"]
        self.input.mouse_down()
        time.sleep(random.uniform(hold_min, hold_max))
        self.input.mouse_up()
        self._cast_point = (x, y)
        self.stats["casts"] += 1
        self.log(f"Cast #{self.stats['casts']}")
        self.state = "WAITING"

    def _wait_bite(self):
        base = self.audio.serial
        now = time.perf_counter()
        ignore_until = now + float(self.s["ignore_after_cast"])
        deadline = now + float(self.s["bite_timeout"])
        while time.perf_counter() < deadline:
            self._check()
            if self.audio.serial > base:
                if time.perf_counter() < ignore_until:
                    base = self.audio.serial
                else:
                    self.stats["bites"] += 1
                    self.log("Bite detected")
                    return True
            time.sleep(0.02)
        self.log("No bite: timeout")
        return False

    def _recover(self):
        self.state = "RECAST"
        self._ensure_focus()
        self._check()
        point = self._cast_point
        if point is None:
            return
        hold = random.uniform(0.08, 0.16)
        self.input.click(point[0], point[1], hold=hold)
        if not self._recover_single:
            time.sleep(0.8)
            self.input.click(point[0], point[1], hold=hold)
        self._recover_single = not self._recover_single
        time.sleep(0.6)

    def _hook(self):
        self.state = "HOOK"
        self._ensure_focus()
        self._check()
        delay = float(self.s["hook_delay"]) + random.uniform(-0.05, 0.08)
        if delay > 0:
            time.sleep(delay)
        point = self._cast_point
        if point is not None:
            current_x, current_y = self.input.position()
            if abs(current_x - point[0]) > 45 or abs(current_y - point[1]) > 45:
                self.input.move_to(point[0], point[1], duration=0.06)
        self.input.mouse_down()
        time.sleep(random.uniform(0.03, 0.06))
        self.input.mouse_up()
        self.state = "REEL"

    def _reel(self):
        analyzer = BarAnalyzer(
            self._template,
            threshold=float(self.s["detection_threshold"]),
            use_green_zone=bool(self.s["use_green_zone"]),
            green_low=tuple(self.s["green_hsv_low"]),
            green_high=tuple(self.s["green_hsv_high"]),
        )
        controller = ReelController(
            deadband=float(self.s["reel_deadband"]),
            lead=float(self.s["reel_lead"]),
            hold_right=self.s["hold_dir"] == "right",
        )
        area = self.s.area()
        timeout = float(self.s["reel_timeout"])
        holding = False
        seen = False
        last_seen = 0.0
        start = time.perf_counter()
        last_focus = start
        frames = 0
        try:
            while True:
                now = time.perf_counter()
                if now - start > timeout:
                    self.log("Mini-game: timeout")
                    break
                if now - last_focus > 0.5:
                    self._ensure_focus()
                    last_focus = now
                roi = self._grabber.grab(area)
                frame = analyzer.analyze(roi, now)
                match = frame.match
                if match is not None:
                    seen = True
                    last_seen = now
                    want_hold = controller.decide(match.cx, frame.target_x, now, holding)
                    if want_hold != holding:
                        if want_hold:
                            self.input.mouse_down()
                        else:
                            self.input.mouse_up()
                        holding = want_hold
                else:
                    if holding and now - last_seen > 0.12:
                        self.input.mouse_up()
                        holding = False
                    if seen and now - last_seen > 0.7:
                        break
                    if not seen and now - start > 2.0:
                        self.log("Mini-game: bar not found")
                        break
                if self.s["debug"] and frames % 20 == 0:
                    self._dump(analyzer, roi, frame, frames)
                frames += 1
                time.sleep(0.004)
        finally:
            if holding:
                self.input.mouse_up()
        self.log(f"Mini-game finished in {time.perf_counter() - start:.1f}s ({frames} frames)")

    def _dump(self, analyzer, roi, frame, frames):
        try:
            folder = self.base / "debug"
            folder.mkdir(exist_ok=True)
            annotated = analyzer.draw(roi, frame)
            name = f"reel_{(frames // 20) % 10}.jpg"
            cv2.imwrite(str(folder / name), annotated)
        except Exception:
            pass

    def _post(self):
        self.state = "PAUSE"
        low, high = self.s["post_delay"]
        time.sleep(random.uniform(low, high))
