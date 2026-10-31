import ctypes
import math
import random
import time
from ctypes import wintypes as wt

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

VK_LBUTTON = 0x01
VK_SPACE = 0x20
VK_F8 = 0x77
VK_F9 = 0x78

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000
KEYEVENTF_KEYUP = 0x0002

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

ULONG_PTR = ctypes.c_size_t


class MOUSEINPUT(ctypes.Structure):
    _fields_ = (
        ("dx", wt.LONG),
        ("dy", wt.LONG),
        ("mouseData", wt.DWORD),
        ("dwFlags", wt.DWORD),
        ("time", wt.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    )


class KEYBDINPUT(ctypes.Structure):
    _fields_ = (
        ("wVk", wt.WORD),
        ("wScan", wt.WORD),
        ("dwFlags", wt.DWORD),
        ("time", wt.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    )


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = (
        ("uMsg", wt.DWORD),
        ("wParamL", wt.WORD),
        ("wParamH", wt.WORD),
    )


class _INPUTUNION(ctypes.Union):
    _fields_ = (("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT))


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = (("type", wt.DWORD), ("u", _INPUTUNION))


WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

user32.SendInput.argtypes = (wt.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
user32.SendInput.restype = wt.UINT
user32.GetCursorPos.argtypes = (ctypes.POINTER(wt.POINT),)
user32.GetAsyncKeyState.argtypes = (ctypes.c_int,)
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetSystemMetrics.argtypes = (ctypes.c_int,)
user32.GetForegroundWindow.restype = wt.HWND
user32.SetForegroundWindow.argtypes = (wt.HWND,)
user32.SetForegroundWindow.restype = wt.BOOL
user32.ShowWindow.argtypes = (wt.HWND, ctypes.c_int)
user32.IsIconic.argtypes = (wt.HWND,)
user32.IsWindowVisible.argtypes = (wt.HWND,)
user32.GetWindowTextLengthW.argtypes = (wt.HWND,)
user32.GetWindowTextW.argtypes = (wt.HWND, wt.LPWSTR, ctypes.c_int)
user32.GetWindowThreadProcessId.argtypes = (wt.HWND, ctypes.POINTER(wt.DWORD))
user32.GetWindowThreadProcessId.restype = wt.DWORD
user32.AttachThreadInput.argtypes = (wt.DWORD, wt.DWORD, wt.BOOL)
user32.EnumWindows.argtypes = (WNDENUMPROC, wt.LPARAM)
user32.BringWindowToTop.argtypes = (wt.HWND,)
user32.VkKeyScanW.argtypes = (ctypes.c_wchar,)
user32.VkKeyScanW.restype = ctypes.c_short
kernel32.GetCurrentThreadId.restype = wt.DWORD
kernel32.OpenProcess.argtypes = (wt.DWORD, wt.BOOL, wt.DWORD)
kernel32.OpenProcess.restype = wt.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = (wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD))
kernel32.CloseHandle.argtypes = (wt.HANDLE,)

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def enable_dpi_awareness():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


enable_dpi_awareness()


def _mouse_input(flags, dx=0, dy=0):
    return INPUT(type=INPUT_MOUSE, u=_INPUTUNION(mi=MOUSEINPUT(dx=dx, dy=dy, mouseData=0, dwFlags=flags, time=0, dwExtraInfo=0)))


def _key_input(vk, flags):
    return INPUT(type=INPUT_KEYBOARD, u=_INPUTUNION(ki=KEYBDINPUT(wVk=vk, wScan=0, dwFlags=flags, time=0, dwExtraInfo=0)))


def _send(event):
    user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))


class Input:
    def __init__(self, enabled=True):
        self.enabled = enabled

    def _guard(self):
        return self.enabled

    def position(self):
        point = wt.POINT()
        user32.GetCursorPos(ctypes.byref(point))
        return point.x, point.y

    def screen_size(self):
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

    def is_down(self, vk):
        return bool(user32.GetAsyncKeyState(vk) & 0x8000)

    def _move_abs(self, x, y):
        vx = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
        vy = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
        vw = max(1, user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))
        vh = max(1, user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))
        nx = int(round((x - vx) * 65535.0 / max(1, vw - 1)))
        ny = int(round((y - vy) * 65535.0 / max(1, vh - 1)))
        _send(_mouse_input(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK, nx, ny))

    def move_to(self, x, y, duration=0.2):
        if not self._guard():
            return
        start_x, start_y = self.position()
        distance = math.hypot(x - start_x, y - start_y)
        if distance < 1.5:
            self._move_abs(x, y)
            return
        duration = max(0.03, min(duration, distance / 1400.0 + 0.05))
        steps = int(max(7, min(45, distance / 13.0)))
        for index in range(1, steps + 1):
            t = index / steps
            eased = t * t * (3.0 - 2.0 * t)
            wobble = (1.0 - eased) * 1.4
            px = start_x + (x - start_x) * eased + random.uniform(-wobble, wobble)
            py = start_y + (y - start_y) * eased + random.uniform(-wobble, wobble)
            self._move_abs(px, py)
            time.sleep(max(0.001, duration / steps))

    def mouse_down(self, button="left"):
        if not self._guard():
            return
        _send(_mouse_input(MOUSEEVENTF_LEFTDOWN if button == "left" else MOUSEEVENTF_RIGHTDOWN))

    def mouse_up(self, button="left"):
        if not self._guard():
            return
        _send(_mouse_input(MOUSEEVENTF_LEFTUP if button == "left" else MOUSEEVENTF_RIGHTUP))

    def click_current(self, hold=0.05, button="left"):
        self.mouse_down(button)
        time.sleep(hold)
        self.mouse_up(button)

    def click(self, x=None, y=None, hold=0.05, button="left"):
        if x is not None and y is not None:
            self.move_to(x, y, duration=0.18)
        self.click_current(hold=hold, button=button)

    def key_press(self, char, hold=0.04):
        if not self._guard():
            return
        vk = user32.VkKeyScanW(ctypes.c_wchar(str(char))) & 0xFF
        if not vk:
            return
        _send(_key_input(vk, 0))
        time.sleep(hold)
        _send(_key_input(vk, KEYEVENTF_KEYUP))

    def windows(self):
        found = []

        def callback(hwnd, _lparam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length:
                    buffer = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buffer, length + 1)
                    found.append((hwnd, buffer.value))
            return True

        user32.EnumWindows(WNDENUMPROC(callback), 0)
        return found

    def window_process(self, hwnd):
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return ""
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if not handle:
            return ""
        try:
            size = wt.DWORD(1024)
            buffer = ctypes.create_unicode_buffer(size.value)
            if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                return buffer.value
            return ""
        finally:
            kernel32.CloseHandle(handle)

    def find_game_window(self, prefix, exclude="Launcher"):
        candidates = []
        for hwnd, title in self.windows():
            if title.startswith(prefix) and exclude not in title:
                candidates.append(hwnd)
        for hwnd in candidates:
            path = self.window_process(hwnd)
            if not path or "albion" in path.lower():
                return hwnd
        return None

    def foreground_title(self):
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ""
        length = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value

    def is_focused(self, prefix, exclude="Launcher"):
        title = self.foreground_title()
        return title.startswith(prefix) and exclude not in title

    def focus_game(self, prefix, exclude="Launcher"):
        hwnd = self.find_game_window(prefix, exclude)
        if not hwnd:
            return False
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)
        current = user32.GetForegroundWindow()
        if current != hwnd:
            thread_fg = user32.GetWindowThreadProcessId(current, None)
            thread_me = kernel32.GetCurrentThreadId()
            attached = False
            if thread_fg and thread_fg != thread_me:
                attached = bool(user32.AttachThreadInput(thread_me, thread_fg, True))
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)
            if attached:
                user32.AttachThreadInput(thread_me, thread_fg, False)
        time.sleep(0.08)
        return self.is_focused(prefix, exclude)

    def failsafe_tripped(self):
        x, y = self.position()
        return x <= 4 and y <= 4
