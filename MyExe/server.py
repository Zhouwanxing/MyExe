import threading
import uvicorn
from fastapi import FastAPI
from typing import Optional
import requests
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
        async def mz(data: Optional[dict] = None):
            res_data = data.get("data", {})
            url = res_data.get("url")
            if not url:
                return {"msg": "missing url"}

            if not ("lianjia.com" in url and "ershoufang" in url):
                return {"msg": "skip url"}

            print(f"URL: {url}")
            cookie = res_data.get("cookie", "")
            print(f"Cookie: {cookie}")

            headers = {"Cookie": cookie,
                       "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"}
            resp = requests.get(url, headers=headers)
            soup = BeautifulSoup(resp.text, "html.parser")
            ul = soup.find(class_="sellListContent")
            if ul is None:
                return {"status": False}
            lis = ul.find_all("li")
            if self.gui_logger:
                self.gui_logger(len(lis))
            for li in lis:
                item_data = handle_lj(li)
                if item_data:
                    if self.gui_logger:
                        self.gui_logger(item_data)
                    requests.post(Config.get("server.baseUrl") + "/page/user/syncLj", json=item_data,
                                           timeout=5)
            return {"status": True}

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
