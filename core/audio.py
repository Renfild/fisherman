import collections
import threading
import time

import numpy as np


class AudioMonitor(threading.Thread):
    def __init__(self, threshold=3000, ratio=2.2, source="auto", logger=None):
        super().__init__(daemon=True, name="audio")
        self.threshold = int(threshold)
        self.ratio = float(ratio)
        self.source = source if source in ("auto", "loopback", "input") else "auto"
        self.log = logger or (lambda message: None)

        self.level = 0
        self.floor = 0
        self.serial = 0
        self.backend = None
        self.last_error = None

        self._peaks = collections.deque(maxlen=400)
        self._next_floor = 0.0
        self._cooldown_until = 0.0
        self._stop_event = threading.Event()

    def update(self, threshold=None, ratio=None):
        if threshold is not None:
            self.threshold = int(threshold)
        if ratio is not None:
            self.ratio = float(ratio)

    def stop(self):
        self._stop_event.set()

    def run(self):
        if self.source == "loopback":
            backends = ["loopback"]
        elif self.source == "input":
            backends = ["input"]
        else:
            backends = ["loopback", "input"]
        for backend in backends:
            if self._stop_event.is_set():
                return
            try:
                self.log(f"Audio: trying {backend}")
                if backend == "loopback":
                    self._run_loopback()
                else:
                    self._run_input()
                return
            except Exception as error:
                self.last_error = repr(error)
                self.log(f"Audio {backend} failed: {error}")
        self.log("Audio unavailable: bite detection disabled")

    def _run_loopback(self):
        import soundcard as sc

        speaker = sc.default_speaker()
        microphone = sc.get_microphone(id=str(speaker.name), include_loopback=True)
        if microphone is None:
            raise RuntimeError("no loopback device")
        self.backend = "loopback"
        self.log(f"Audio: loopback of '{speaker.name}'")
        with microphone.recorder(samplerate=48000, channels=1, blocksize=512) as recorder:
            while not self._stop_event.is_set():
                data = recorder.record(numframes=512)
                self._process(np.asarray(data[:, 0], dtype=np.float32))

    def _run_input(self):
        import pyaudio

        client = pyaudio.PyAudio()
        self.backend = "input"
        self.log("Audio: input device (select Stereo Mix as default recording device)")
        stream = client.open(format=pyaudio.paInt16, channels=2, rate=44100,
                             input=True, frames_per_buffer=512)
        try:
            while not self._stop_event.is_set():
                raw = stream.read(512, exception_on_overflow=False)
                samples = np.frombuffer(raw, dtype=np.int16)
                if samples.size >= 2:
                    samples = samples.reshape(-1, 2).mean(axis=1)
                self._process(samples.astype(np.float32) / 32768.0)
        finally:
            stream.stop_stream()
            stream.close()
            client.terminate()

    def _process(self, samples):
        if samples.size < 32:
            return
        transient = np.diff(samples)
        peak = int(min(32767.0, float(np.abs(transient).max()) * 65534.0))
        now = time.perf_counter()

        self.level = peak
        self._peaks.append((now, peak))
        while self._peaks and now - self._peaks[0][0] > 4.0:
            self._peaks.popleft()

        if now >= self._next_floor and len(self._peaks) >= 24:
            values = [value for _, value in self._peaks]
            self.floor = int(np.percentile(values, 80))
            self._next_floor = now + 0.5

        trigger = max(self.threshold, int(self.floor * self.ratio))
        if now < self._cooldown_until or peak <= trigger:
            return
        self._cooldown_until = now + 1.2
        self.serial += 1
        self.log(f"Sound: peak {peak} > {trigger} -> bite")
