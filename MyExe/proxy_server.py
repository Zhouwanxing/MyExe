import asyncio
import threading
import time
from urllib.parse import urlparse

import requests
from fastapi import FastAPI, Request
from fastapi.responses import Response
from uvicorn import Config as UvicornConfig, Server

HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host",
}


class ProxyServer:
    def __init__(self, host="0.0.0.0", port=8080, target_url="", gui_logger=None):
        self.host = host
        self.port = port
        self.target_url = target_url.rstrip("/") if target_url else ""
        self.gui_logger = gui_logger
        self.running = False
        self.thread = None
        self.uvicorn_server = None
        self._stop_requested = False
        self.app = self._build_app()

    def _build_app(self):
        app = FastAPI()
        server = self

        @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
        async def proxy(request: Request, path: str = ""):
            if not server.target_url:
                return Response(content="未配置转发目标地址", status_code=502)

            target = server.target_url
            if path:
                target = f"{target}/{path}"

            query = request.url.query
            if query:
                target = f"{target}?{query}"

            headers = {
                k: v for k, v in request.headers.items()
                if k.lower() not in HOP_BY_HOP
            }
            body = await request.body()

            if server.gui_logger:
                server.gui_logger(f"[Proxy] {request.method} {request.url.path} -> {target}")

            loop = asyncio.get_event_loop()
            try:
                resp = await loop.run_in_executor(
                    None,
                    lambda: requests.request(
                        method=request.method,
                        url=target,
                        headers=headers,
                        data=body if body else None,
                        allow_redirects=False,
                        timeout=60,
                    ),
                )
            except requests.RequestException as e:
                if server.gui_logger:
                    server.gui_logger(f"[Proxy] 转发失败: {e}", tag="error")
                return Response(content=f"转发失败: {e}", status_code=502)

            resp_headers = {
                k: v for k, v in resp.headers.items()
                if k.lower() not in HOP_BY_HOP
            }
            return Response(content=resp.content, status_code=resp.status_code, headers=resp_headers)

        return app

    def configure(self, port, target_url):
        self.port = int(port)
        self.target_url = target_url.rstrip("/")

    def start(self):
        if not self.target_url:
            if self.gui_logger:
                self.gui_logger("[Proxy] 请先配置目标地址", tag="warn")
            return False

        parsed = urlparse(self.target_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            if self.gui_logger:
                self.gui_logger("[Proxy] 目标地址格式无效，需以 http:// 或 https:// 开头", tag="warn")
            return False

        if self.thread and self.thread.is_alive():
            if self.gui_logger:
                self.gui_logger("[Proxy] 转发服务已在运行或正在停止中")
            return False

        self._stop_requested = False
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        if self.gui_logger:
            self.gui_logger(f"[Proxy] 端口 {self.port} -> {self.target_url}")
        return True

    def _run(self):
        if self._stop_requested:
            self.running = False
            return

        config = UvicornConfig(self.app, host=self.host, port=self.port, log_level="warning")
        server = Server(config)
        self.uvicorn_server = server
        try:
            server.run()
        finally:
            self.uvicorn_server = None
            self.running = False

    def stop(self, timeout=10):
        if not self.running and (self.thread is None or not self.thread.is_alive()):
            return

        self._stop_requested = True
        if self.gui_logger:
            self.gui_logger("[Proxy] 正在停止端口转发...")

        deadline = time.time() + 5
        while self.uvicorn_server is None and time.time() < deadline:
            if self.thread is None or not self.thread.is_alive():
                break
            time.sleep(0.05)

        if self.uvicorn_server is not None:
            self.uvicorn_server.should_exit = True

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=timeout)

        self.running = False
        if self.gui_logger:
            if self.thread and self.thread.is_alive():
                self.gui_logger("[Proxy] 停止超时，请稍后再试", tag="warn")
            else:
                self.gui_logger("[Proxy] 端口转发已停止")
