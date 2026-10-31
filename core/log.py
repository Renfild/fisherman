import queue
import time
from collections import deque
from pathlib import Path


class Logger:
    def __init__(self, path, echo=False):
        self.path = Path(path)
        self.echo = echo
        self.queue = queue.Queue()
        self.lines = deque(maxlen=500)
        self._file = None
        try:
            self._file = self.path.open("a", encoding="utf-8", buffering=1)
        except OSError:
            pass

    def log(self, message):
        line = f"[{time.strftime('%H:%M:%S')}] {message}"
        self.lines.append(line)
        self.queue.put(line)
        if self.echo:
            print(line, flush=True)
        if self._file:
            try:
                self._file.write(line + "\n")
            except OSError:
                pass

    __call__ = log

    def drain(self, limit=40):
        lines = []
        for _ in range(limit):
            try:
                lines.append(self.queue.get_nowait())
            except queue.Empty:
                break
        return lines

    def close(self):
        if self._file:
            try:
                self._file.close()
            except OSError:
                pass
            self._file = None
