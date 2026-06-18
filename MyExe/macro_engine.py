import os
import subprocess
import threading
import time
import webbrowser

import pyautogui

try:
    from pynput import keyboard, mouse
except ImportError:
    keyboard = None
    mouse = None

try:
    from utils.config_loader import Config
except ImportError:
    from MyExe.utils.config_loader import Config

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

DEFAULT_WAIT = 5
STOP_HOTKEY = keyboard.Key.f9 if keyboard else None


def open_browser(url, logger=None):
    chrome_path = Config.get("server.chromePath")
    if chrome_path and os.path.exists(chrome_path):
        try:
            subprocess.Popen([chrome_path, url, "--new-window"])
            if logger:
                logger(f"[Macro] 已通过 Chrome 打开: {url}")
            return
        except OSError as e:
            if logger:
                logger(f"[Macro] Chrome 启动失败，改用默认浏览器: {e}", tag="warn")
    webbrowser.open(url, new=1)
    if logger:
        logger(f"[Macro] 已通过默认浏览器打开: {url}")


class MacroRecorder:
    """录制鼠标与键盘操作，按 F9 或调用 stop() 结束。"""

    def __init__(self, logger=None):
        self.logger = logger
        self.recording = False
        self.events = []
        self._start_time = 0.0
        self._last_time = 0.0
        self._mouse_listener = None
        self._key_listener = None
        self._lock = threading.Lock()
        self._stop_requested = False

    def _elapsed(self):
        now = time.time()
        delay = round(now - self._last_time, 4)
        self._last_time = now
        return delay

    def _log(self, msg, tag="info"):
        if self.logger:
            self.logger(msg, tag=tag)

    def _on_click(self, x, y, button, pressed):
        if not self.recording or not pressed:
            return
        btn = "left" if button == mouse.Button.left else "right"
        with self._lock:
            self.events.append({"type": "click", "x": x, "y": y, "button": btn, "delay": self._elapsed()})

    def _on_scroll(self, x, y, dx, dy):
        if not self.recording:
            return
        with self._lock:
            self.events.append({"type": "scroll", "x": x, "y": y, "dy": dy, "delay": self._elapsed()})

    def _on_key(self, key, pressed):
        if not self.recording:
            return
        if key == STOP_HOTKEY and pressed:
            self._stop_requested = True
            return
        if key == STOP_HOTKEY:
            return
        try:
            key_str = key.char if hasattr(key, "char") and key.char else str(key)
        except AttributeError:
            key_str = str(key)
        with self._lock:
            self.events.append({
                "type": "key_down" if pressed else "key_up",
                "key": key_str,
                "delay": self._elapsed(),
            })

    def start(self, countdown=3):
        if keyboard is None or mouse is None:
            raise RuntimeError("缺少 pynput 库，请执行 pip install pynput")
        if self.recording:
            return False

        self.events = []
        self._stop_requested = False
        self.recording = True
        self._start_time = time.time()
        self._last_time = self._start_time

        self._mouse_listener = mouse.Listener(on_click=self._on_click, on_scroll=self._on_scroll)
        self._key_listener = keyboard.Listener(on_press=lambda k: self._on_key(k, True),
                                               on_release=lambda k: self._on_key(k, False))
        self._mouse_listener.start()
        self._key_listener.start()
        self._log(f"[Macro] 录制已开始，按 F9 结束录制（{countdown}s 后生效）")
        return True

    def stop(self):
        self.recording = False
        self._stop_requested = True
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None
        if self._key_listener:
            self._key_listener.stop()
            self._key_listener = None
        with self._lock:
            count = len(self.events)
        self._log(f"[Macro] 录制已停止，共 {count} 个事件", tag="success")
        return list(self.events)

    def wait_until_stopped(self, poll=0.2):
        while self.recording and not self._stop_requested:
            time.sleep(poll)
        return self.stop()


class MacroPlayer:
    """回放已录制的操作。"""

    def __init__(self, logger=None):
        self.logger = logger
        self.playing = False

    def _log(self, msg, tag="info"):
        if self.logger:
            self.logger(msg, tag=tag)

    def play(self, macro, wait_seconds=None):
        if self.playing:
            self._log("[Macro] 已有任务正在执行", tag="warn")
            return False

        url = macro.get("url", "")
        events = macro.get("events", [])
        if not events:
            self._log("[Macro] 录制为空，无法执行", tag="warn")
            return False

        wait = wait_seconds if wait_seconds is not None else macro.get("wait_seconds", DEFAULT_WAIT)
        name = macro.get("name", macro.get("id", "未命名"))

        self.playing = True
        try:
            if url:
                open_browser(url, self._log)
                self._log(f"[Macro] 等待页面加载 {wait}s ...")
                time.sleep(wait)

            self._log(f"[Macro] 开始执行「{name}」，共 {len(events)} 步")
            for i, ev in enumerate(events):
                delay = ev.get("delay", 0)
                if delay > 0:
                    time.sleep(delay)
                self._execute_event(ev)

            self._log(f"[Macro] 「{name}」执行完成", tag="success")
            return True
        except pyautogui.FailSafeException:
            self._log("[Macro] 鼠标移至屏幕角落，执行已中止（安全机制）", tag="warn")
            return False
        except Exception as e:
            self._log(f"[Macro] 执行失败: {e}", tag="error")
            return False
        finally:
            self.playing = False

    def _execute_event(self, ev):
        t = ev.get("type")
        if t == "click":
            btn = ev.get("button", "left")
            pyautogui.click(ev["x"], ev["y"], button=btn)
        elif t == "scroll":
            pyautogui.scroll(int(ev.get("dy", 0)), x=ev.get("x"), y=ev.get("y"))
        elif t == "key_down":
            key = self._normalize_key(ev.get("key", ""))
            if key:
                pyautogui.keyDown(key)
        elif t == "key_up":
            key = self._normalize_key(ev.get("key", ""))
            if key:
                pyautogui.keyUp(key)

    @staticmethod
    def _normalize_key(key_str):
        if not key_str:
            return None
        mapping = {
            "Key.enter": "enter",
            "Key.tab": "tab",
            "Key.backspace": "backspace",
            "Key.delete": "delete",
            "Key.esc": "esc",
            "Key.space": "space",
            "Key.shift": "shift",
            "Key.shift_r": "shiftright",
            "Key.ctrl": "ctrl",
            "Key.ctrl_l": "ctrlleft",
            "Key.ctrl_r": "ctrlright",
            "Key.alt": "alt",
            "Key.alt_l": "altleft",
            "Key.alt_r": "altright",
            "Key.up": "up",
            "Key.down": "down",
            "Key.left": "left",
            "Key.right": "right",
            "Key.home": "home",
            "Key.end": "end",
            "Key.page_up": "pageup",
            "Key.page_down": "pagedown",
        }
        if key_str in mapping:
            return mapping[key_str]
        if key_str.startswith("Key."):
            return key_str[4:]
        if len(key_str) == 1:
            return key_str
        return key_str
