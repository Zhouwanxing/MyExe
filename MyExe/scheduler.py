import threading
import time

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
            time.sleep(self.interval)

    def stop(self):
        self.running = False
        if self.gui_logger:
            self.gui_logger("[Scheduler] Stopped")
