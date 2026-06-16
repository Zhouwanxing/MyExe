import threading
import time
from uvicorn import Config as UvicornConfig, Server
from fastapi import FastAPI
from typing import Optional
import requests
import uuid

from bs4 import BeautifulSoup

try:
    from utils.config_loader import Config
except ImportError:
    from MyExe.utils.config_loader import Config


def handle_lj(element):
    data = {}
    try:
        link_tag = element.find(class_="noresultRecommend")
        if not link_tag:
            return None
        attr = link_tag.get("href")
        data["linkUrl"] = attr

        split = attr.split("/")
        data["_id"] = split[-1].split(".")[0]

        title_tag = element.find(class_="lj-lazy")
        data["title"] = title_tag.get("alt") if title_tag else ""

        house_info = element.find(class_="houseInfo")
        data["info"] = house_info.get_text(strip=True) if house_info else ""

        price_info = element.find(class_="priceInfo")
        data["priceStr"] = price_info.get_text(strip=True) if price_info else ""
        return data
    except Exception as e:
        print(f"解析异常: {e}")
        return None


class FastAPIServer:
    def __init__(self, host="0.0.0.0", port=4000, gui_logger=None):
        self.host = host
        self.port = port
        self.running = False
        self.thread = None
        self.uvicorn_server = None
        self._stop_requested = False
        self.app = FastAPI()
        self.gui_logger = gui_logger

        # 注册路由
        @self.app.get("/")
        def root(skip: int = 0, limit: int = 10, name: str = ""):
            if self.gui_logger:
                self.gui_logger("[Server] Received HTTP request")
            return {"message": "Hello from MyExe FastAPI server!"}

        @self.app.get("/items/{item_id}")
        async def read_item(item_id: int):
            return {"item_id": item_id}

        @self.app.post("/page/user/mz")
        def mz(data: Optional[dict] = None):
            res_data = data.get("data", {})
            url = res_data.get("url")
            if self.gui_logger:
                self.gui_logger(f"{url}")
            if not url:
                return {"msg": "missing url"}

            if not ("lianjia.com" in url and "ershoufang" in url):
                return {"msg": "skip url"}

            random_uuid = uuid.uuid4()
            # if self.gui_logger:
            #     self.gui_logger(f"URL: {url}")
            cookie = res_data.get("cookie", "")
            # if self.gui_logger:
            #     self.gui_logger(f"Cookie: {cookie}")

            headers = {"Cookie": cookie,
                       "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"}
            resp = requests.get(url, headers=headers)
            soup = BeautifulSoup(resp.text, "html.parser")
            ul = soup.find(class_="sellListContent")
            if ul is None:
                return {"status": False}
            lis = ul.find_all("li")
            if self.gui_logger:
                self.gui_logger(f"{random_uuid}={len(lis)}")
            for li in lis:
                item_data = handle_lj(li)
                if item_data:
                    # if self.gui_logger:
                    #     self.gui_logger(item_data)
                    requests.post(Config.get("server.baseUrl") + "/page/user/syncLj", json=item_data,
                                           timeout=5)
            if self.gui_logger:
                self.gui_logger(f"{random_uuid}=end...")
            return {"status": True}

    def start(self):
        if self.thread and self.thread.is_alive():
            if self.gui_logger:
                self.gui_logger("[Server] 服务已在运行或正在停止中")
            return

        self._stop_requested = False
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        if self.gui_logger:
            self.gui_logger(f"[Server] FastAPI started on {self.host}:{self.port}")

    def _run(self):
        if self._stop_requested:
            self.running = False
            return

        config = UvicornConfig(self.app, host=self.host, port=self.port, log_level="info")
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
            self.gui_logger("[Server] 正在停止 FastAPI...")

        # 等待 uvicorn Server 实例创建（启动瞬间点停止的情况）
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
                self.gui_logger("[Server] FastAPI 停止超时，请稍后再试", tag="warn")
            else:
                self.gui_logger("[Server] FastAPI 已停止，端口已释放")
