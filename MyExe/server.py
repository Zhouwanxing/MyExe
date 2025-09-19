import threading
import uvicorn
from fastapi import FastAPI

class FastAPIServer:
    def __init__(self, host="0.0.0.0", port=4000, gui_logger=None):
        self.host = host
        self.port = port
        self.running = False
        self.thread = None
        self.app = FastAPI()
        self.gui_logger = gui_logger

        # 注册路由
        @self.app.get("/")
        def root():
            if self.gui_logger:
                self.gui_logger("[Server] Received HTTP request")
            return {"message": "Hello from MyExe FastAPI server!"}

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        if self.gui_logger:
            self.gui_logger(f"[Server] FastAPI started on {self.host}:{self.port}")

    def _run(self):
        uvicorn.run(self.app, host=self.host, port=self.port, log_level="info")

    def stop(self):
        self.running = False
        if self.gui_logger:
            self.gui_logger("[Server] FastAPI stopped (请重启应用以释放端口)")
