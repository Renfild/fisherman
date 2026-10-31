import collections


class ReelController:
    def __init__(self, deadband=6.0, lead=0.08, hold_right=True):
        self.deadband = float(deadband)
        self.lead = float(lead)
        self.sign = 1.0 if hold_right else -1.0
        self._history = collections.deque(maxlen=48)
        self._last_holding = None
        self._state_since = None

    def reset(self):
        self._history.clear()
        self._last_holding = None
        self._state_since = None

    def _velocity(self, now):
        points = [point for point in self._history if now - point[0] <= 0.18]
        if len(points) < 3:
            return 0.0
        t0, x0 = points[0]
        t1, x1 = points[-1]
        dt = t1 - t0
        if dt <= 1e-6:
            return 0.0
        return (x1 - x0) / dt

    def decide(self, x, target, now, holding):
        self._history.append((now, x))
        if holding != self._last_holding:
            self._last_holding = holding
            self._state_since = now
        velocity = 0.0
        if self._state_since is not None and now - self._state_since >= 0.10:
            velocity = self._velocity(now)
        predicted = x + velocity * self.lead
        relative = (predicted - target) * self.sign
        limit = 0.25 * self.deadband if holding else -0.75 * self.deadband
        return relative < limit
