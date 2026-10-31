import argparse
import sys
import threading
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

import cv2
import dearpygui.dearpygui as dpg

from core.audio import AudioMonitor
from core.bot import Bot
from core.capture import Grabber
from core.config import Settings
from core.input import VK_SPACE
from core.log import Logger
from core.vision import BarAnalyzer, load_template


class App:
    def __init__(self, settings, bot, audio, logger):
        self.settings = settings
        self.bot = bot
        self.audio = audio
        self.logger = logger
        self._preview_stop = threading.Event()
        self._preview_thread = None
        self._log_dirty = False
        self._ticks = 0

    def run(self):
        dpg.create_context()
        self._build()
        dpg.create_viewport(title="Fisherman v3.0 - Albion Online", width=660, height=800)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("main", True)
        while dpg.is_dearpygui_running():
            self._tick()
            dpg.render_dearpygui_frame()
        dpg.destroy_context()

    def _build(self):
        s = self.settings
        with dpg.window(label="Albion Fisherman", width=640, height=780, tag="main"):
            with dpg.group(horizontal=True):
                dpg.add_button(label="LOAD", width=90, callback=self.on_load)
                dpg.add_button(label="SAVE", width=90, callback=self.on_save)
            dpg.add_separator()
            dpg.add_button(label="1. Add fishing spot (Space)", width=300, callback=self.on_add_spot)
            dpg.add_button(label="2. Set tracking zone (Space)", width=300, callback=self.on_set_zone)
            dpg.add_button(label="3. Setup bait: slot + use (Space)", width=300, callback=self.on_set_bait)
            dpg.add_button(label="4. Set anti-fatigue point (Space)", width=300, callback=self.on_set_move)
            dpg.add_button(label="Clear spots", width=300, callback=self.on_clear_spots)
            dpg.add_separator()
            dpg.add_input_int(label="Volume threshold", default_value=int(s["volume_threshold"]),
                              width=130, step=100, tag="vol_input", callback=self.on_volume)
            dpg.add_input_float(label="Detection threshold", default_value=float(s["detection_threshold"]),
                                width=130, step=0.02, format="%.2f", tag="det_input", callback=self.on_flags)
            with dpg.group(horizontal=True):
                dpg.add_checkbox(label="Aim at green zone", default_value=bool(s["use_green_zone"]),
                                 tag="green_check", callback=self.on_flags)
                dpg.add_text("   hold pushes")
                dpg.add_combo(items=["right", "left"], default_value=s["hold_dir"], width=85,
                              tag="hold_combo", callback=self.on_flags)
            dpg.add_checkbox(label="Require Albion focus", default_value=bool(s["require_focus"]),
                             tag="focus_check", callback=self.on_flags)
            with dpg.group(horizontal=True):
                dpg.add_button(label="Auto threshold", width=145, callback=self.on_auto_threshold)
                dpg.add_button(label="Test zone", width=145, callback=self.on_test_zone)
            dpg.add_separator()
            with dpg.group(horizontal=True):
                dpg.add_button(label="START  (F8)", width=145, height=42, callback=self.on_start)
                dpg.add_button(label="STOP  (F9)", width=145, height=42, callback=self.on_stop)
            dpg.add_text("IDLE", tag="status")
            with dpg.group(horizontal=True):
                dpg.add_progress_bar(default_value=0.0, width=240, height=16, tag="level_bar")
                dpg.add_text("level 0", tag="level_text")
            dpg.add_text("", tag="spots_info")
            dpg.add_separator()
            with dpg.child_window(tag="log_window", height=215, width=-1):
                dpg.add_group(tag="log_group")
        self._refresh_info()

    def _tick(self):
        for line in self.logger.drain():
            dpg.add_text(line, parent="log_group", wrap=580)
            self._log_dirty = True
        self._ticks += 1
        if self._log_dirty and self._ticks % 6 == 0:
            dpg.set_y_scroll("log_window", -1.0)
            self._log_dirty = False

        status = self.bot.status()
        state = status["state"] if status["armed"] else "IDLE"
        dpg.set_value(
            "status",
            f"{state}   |   casts {status['casts']}   |   bites {status['bites']}   |   reels {status['reels']}",
        )
        level = int(self.audio.level)
        dpg.set_value("level_bar", min(1.0, level / 20000.0))
        dpg.set_value(
            "level_text",
            f"level {level}   floor {self.audio.floor}   thr {self.audio.threshold}   audio: {self.audio.backend or '-'}",
        )

    def _refresh_info(self):
        area = self.settings.area()
        dpg.set_value(
            "spots_info",
            f"spots: {len(self.settings.coords())}   zone: {area['width']}x{area['height']} at ({area['left']},{area['top']})",
        )

    def _pull_ui(self):
        s = self.settings
        s["volume_threshold"] = int(dpg.get_value("vol_input"))
        s["detection_threshold"] = float(dpg.get_value("det_input"))
        s["use_green_zone"] = bool(dpg.get_value("green_check"))
        s["require_focus"] = bool(dpg.get_value("focus_check"))
        s["hold_dir"] = dpg.get_value("hold_combo")
        self.audio.update(threshold=s["volume_threshold"], ratio=s["audio_ratio"])

    def _push_ui(self):
        s = self.settings
        dpg.set_value("vol_input", int(s["volume_threshold"]))
        dpg.set_value("det_input", float(s["detection_threshold"]))
        dpg.set_value("green_check", bool(s["use_green_zone"]))
        dpg.set_value("focus_check", bool(s["require_focus"]))
        dpg.set_value("hold_combo", s["hold_dir"])
        self._refresh_info()

    def _wait_space(self):
        inp = self.bot.input
        while inp.is_down(VK_SPACE):
            time.sleep(0.01)
        while not inp.is_down(VK_SPACE):
            time.sleep(0.01)
        position = inp.position()
        while inp.is_down(VK_SPACE):
            time.sleep(0.01)
        return position

    def _pick(self, prompt):
        self.logger.log(prompt)
        return self._wait_space()

    def on_add_spot(self, *args):
        threading.Thread(target=self._add_spot, daemon=True).start()

    def _add_spot(self):
        point = self._pick("Hover a cast spot and press SPACE")
        self.settings.add_spot(*point)
        self.logger.log(f"Spot added: {point}")
        self._refresh_info()

    def on_set_zone(self, *args):
        threading.Thread(target=self._set_zone, daemon=True).start()

    def _set_zone(self):
        first = self._pick("Zone: hover TOP-LEFT corner of the mini-game bar and press SPACE")
        second = self._pick("Zone: hover BOTTOM-RIGHT corner and press SPACE")
        left, top = min(first[0], second[0]), min(first[1], second[1])
        width, height = abs(second[0] - first[0]), abs(second[1] - first[1])
        self.settings.set_area(left, top, width, height)
        self.logger.log(f"Tracking zone set: {width}x{height} at ({left},{top})")
        self._refresh_info()

    def on_set_bait(self, *args):
        threading.Thread(target=self._set_bait, daemon=True).start()

    def _set_bait(self):
        slot = self._pick("Bait: hover the bait slot in inventory and press SPACE")
        use = self._pick("Bait: hover the USE button and press SPACE")
        self.settings.set_point("bait_step1", slot)
        self.settings.set_point("bait_step2", use)
        self.logger.log(f"Bait points: {slot} -> {use}")

    def on_set_move(self, *args):
        threading.Thread(target=self._set_move, daemon=True).start()

    def _set_move(self):
        point = self._pick("Anti-fatigue: hover a walk point and press SPACE")
        self.settings.set_point("move_spot", point)
        self.logger.log(f"Move point: {point}")

    def on_clear_spots(self, *args):
        self.settings.clear_spots()
        self.logger.log("Spots cleared")
        self._refresh_info()

    def on_volume(self, *args):
        value = int(dpg.get_value("vol_input"))
        self.settings["volume_threshold"] = value
        self.audio.update(threshold=value)

    def on_flags(self, *args):
        self._pull_ui()

    def on_auto_threshold(self, *args):
        floor = int(self.audio.floor)
        value = max(1200, floor * 3)
        dpg.set_value("vol_input", value)
        self.settings["volume_threshold"] = value
        self.audio.update(threshold=value)
        self.logger.log(f"Auto threshold: floor {floor} -> {value}")

    def on_save(self, *args):
        self._pull_ui()
        self.settings.save()
        self.logger.log("Settings saved")
        self._refresh_info()

    def on_load(self, *args):
        self.settings.load()
        self._push_ui()
        self.logger.log("Settings loaded")

    def on_start(self, *args):
        self._pull_ui()
        self.settings.save()
        self.bot.start_bot()

    def on_stop(self, *args):
        self.bot.stop_bot()

    def on_test_zone(self, *args):
        if self._preview_thread is not None and self._preview_thread.is_alive():
            self.logger.log("Preview already open (press q in its window)")
            return
        self._preview_stop.clear()
        self._preview_thread = threading.Thread(target=self._preview_loop, daemon=True)
        self._preview_thread.start()

    def _preview_loop(self):
        window = None
        area = self.settings.area()
        if area["width"] < 60 or area["height"] < 20:
            self.logger.log("Test zone: tracking zone is not set")
            return
        try:
            grabber = Grabber()
            analyzer = BarAnalyzer(
                load_template(BASE / "bobber.png"),
                threshold=float(self.settings["detection_threshold"]),
                use_green_zone=bool(self.settings["use_green_zone"]),
                green_low=tuple(self.settings["green_hsv_low"]),
                green_high=tuple(self.settings["green_hsv_high"]),
            )
            window = "Fisherman zone preview (q to close)"
            while not self._preview_stop.is_set():
                roi = grabber.grab(area)
                frame = analyzer.analyze(roi)
                view = analyzer.draw(roi, frame)
                height, width = view.shape[:2]
                scale = max(1.0, min(2.5, 1100.0 / max(1, width)))
                view = cv2.resize(view, (int(width * scale), int(height * scale)))
                cv2.imshow(window, view)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
                if cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
                    break
                time.sleep(0.01)
            grabber.close()
        except Exception as error:
            self.logger.log(f"Preview error: {error!r}")
        finally:
            self._preview_stop.set()
            if window is not None:
                try:
                    cv2.destroyWindow(window)
                except Exception:
                    pass

    def shutdown(self):
        self._preview_stop.set()
        self.bot.shutdown()
        self.bot.join(timeout=1.5)
        self.audio.stop()
        self.audio.join(timeout=1.0)
        self.logger.close()


def main():
    parser = argparse.ArgumentParser(description="Fisherman - Albion Online fishing bot")
    parser.add_argument("--headless", action="store_true", help="run without GUI, settings from settings.ini")
    parser.add_argument("--selftest", action="store_true", help="run diagnostics and exit")
    args = parser.parse_args()

    settings = Settings(BASE / "settings.ini")
    logger = Logger(BASE / "fisherman.log", echo=args.headless or args.selftest)

    if args.selftest:
        from core.selftest import run as selftest_run
        sys.exit(selftest_run(settings, logger, BASE))

    audio = AudioMonitor(settings["volume_threshold"], settings["audio_ratio"],
                         settings["audio_source"], logger)
    audio.start()
    bot = Bot(settings, audio, logger, BASE)
    bot.start()

    if args.headless:
        if bot.start_bot():
            try:
                while True:
                    time.sleep(0.5)
            except KeyboardInterrupt:
                logger.log("Interrupted")
        bot.shutdown()
        audio.stop()
        logger.close()
        return

    app = App(settings, bot, audio, logger)
    try:
        app.run()
    finally:
        app.shutdown()


if __name__ == "__main__":
    main()
