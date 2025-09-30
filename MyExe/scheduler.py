import threading
import time
import subprocess
import pyautogui

try:
    from utils.config_loader import Config
except ImportError:
    from MyExe.utils.config_loader import Config


def openPage():
    scroll_height = -19500
    scroll_height2 = 760
    click_page_y = 260

    subprocess.Popen([Config.get("server.chromePath"), Config.get("server.clickUrl")])
    time.sleep(10)
    subprocess.Popen([Config.get("server.chromePath"), Config.get("server.clickUrl")])
    time.sleep(10)
    pyautogui.click(570, 678)
    time.sleep(1)
    pyautogui.click(560, 783)
    for i in range(6):
        time.sleep(10)
        pyautogui.scroll(scroll_height)
        time.sleep(2)
        pyautogui.scroll(scroll_height2)
        time.sleep(1)
        pyautogui.scroll(scroll_height)
        time.sleep(2)
        pyautogui.scroll(scroll_height2)
        time.sleep(1)
        pyautogui.click(1165 + i * 45, click_page_y)


class SimpleScheduler:
    def __init__(self, interval=5, gui_logger=None):
        self.interval = interval
        self.running = False
        self.thread = None
        self.gui_logger = gui_logger

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        if self.gui_logger:
            self.gui_logger("[Scheduler] Started")

    def run(self):
        while self.running:
            if self.gui_logger:
                self.gui_logger("[Scheduler] Running task...")
            openPage()
            time.sleep(self.interval)

    def stop(self):
        self.running = False
        if self.gui_logger:
            self.gui_logger("[Scheduler] Stopped")
