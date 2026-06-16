import json
import threading
import time
import requests
from bs4 import BeautifulSoup

try:
    from utils.config_loader import Config
except ImportError:
    from MyExe.utils.config_loader import Config

TASK_LIST_URL = Config.get("server.baseUrl", "https://goldtask.onrender.com") + "/house/getBodyFromComputer"
DEFAULT_INTERVAL = 5 * 60 * 60

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    ),
}


def _extract_body_html(html_text):
    soup = BeautifulSoup(html_text, "html.parser")
    body = soup.find("body")
    if body:
        return body.decode_contents()
    return html_text

def _result_has_error_text(text, errorText):
    if not text or not text.strip():
        return False, ""
    return errorText in text


def _response_is_empty(text):
    if not text or not text.strip():
        return True, "接口返回为空"
    return False, ""


class SimpleScheduler:
    def __init__(self, interval=DEFAULT_INTERVAL, gui_logger=None, on_pause=None):
        self.interval = interval
        self.running = False
        self.paused = False
        self.thread = None
        self.gui_logger = gui_logger
        self.on_pause = on_pause
        self._pause_reason = ""
        self._pending_tasks = []
        self._task_index = 0
        self._lock = threading.Lock()
        self._resume_event = threading.Event()
        self._resume_event.set()

    def start(self):
        if self.running:
            return
        self.running = True
        self.paused = False
        self._pause_reason = ""
        self._pending_tasks = []
        self._task_index = 0
        self._resume_event.set()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        if self.gui_logger:
            self.gui_logger("[Scheduler] 默认定时任务已启动，立即执行第一轮（之后每 5 小时执行）")

    def stop(self):
        self.running = False
        self.paused = False
        self._resume_event.set()
        if self.gui_logger:
            self.gui_logger("[Scheduler] 已停止")

    def resume(self):
        with self._lock:
            if not self.running or not self.paused:
                return False
            self.paused = False
            self._pause_reason = ""
            self._pending_tasks = []
            self._task_index = 0
            self._resume_event.set()
        if self.gui_logger:
            self.gui_logger("[Scheduler] 已恢复执行，重新从接口获取任务")
        return True

    def _log(self, msg, tag="info"):
        if self.gui_logger:
            self.gui_logger(msg, tag=tag)

    def _pause(self, reason):
        with self._lock:
            self.paused = True
            self._pause_reason = reason
            self._resume_event.clear()
        self._log(f"[Scheduler] 任务已暂停: {reason}", tag="warn")
        if self.on_pause:
            self.on_pause(reason)

    def _fetch_task_list(self):
        self._log(f"[Scheduler] 正在获取任务列表: {TASK_LIST_URL}")
        resp = requests.get(TASK_LIST_URL, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            self._log("[Scheduler] 任务列表为空")
            return []
        if isinstance(data, dict):
            return [data]
        return list(data)

    def _process_single_task(self, task):
        url = task.get("url", "")
        to_url = task.get("to", "")
        errorText = task.get("errorText", "")
        if not url or not to_url:
            return True, "任务缺少 url 或 to 字段"

        try:
            self._log(f"[Scheduler] GET {url}")
            resp = requests.get(url, headers=HEADERS, timeout=60)
            resp.raise_for_status()
            text = resp.text
            self._log(f"[Scheduler] GET 成功，响应长度 {len(text)} 字节")
        except Exception as e:
            return True, f"GET 请求异常: {e}"

        has_error, reason = _response_is_empty(text)
        if has_error:
            return True, f"{url} — {reason}"

        has_error = _result_has_error_text(text,errorText)
        if has_error:
            self._log(f"[Scheduler] GET 结果含 {errorText}", tag="warn")
            return True, f"{url} — {errorText}"

        body_html = _extract_body_html(text)
        payload = {"url": url, "body": body_html}
        try:
            self._log(f"[Scheduler] POST {to_url}")
            post_resp = requests.post(to_url, json=payload, headers=HEADERS, timeout=60)
            post_resp.raise_for_status()
            self._log(
                f"[Scheduler] POST 成功，状态码 {post_resp.status_code}，body 长度 {len(body_html)} 字节",
                tag="success",
            )
        except Exception as e:
            return True, f"POST 转发异常: {e}"

        self._log(f"[Scheduler] 任务完成: {url}", tag="success")
        return False, ""

    def _execute_batch(self, tasks, start_index=0):
        for i in range(start_index, len(tasks)):
            if not self.running:
                return
            self._task_index = i
            self._pending_tasks = tasks
            task = tasks[i]
            url = task.get("url", "")
            self._log(f"[Scheduler] 正在处理 ({i + 1}/{len(tasks)}): {url}")
            should_pause, reason = self._process_single_task(task)
            if should_pause:
                self._pause(reason)
                return

        self._pending_tasks = []
        self._task_index = 0
        self._log("[Scheduler] 本轮任务全部完成，5 小时后执行下一轮", tag="success")

    def _run_pending_or_fetch(self):
        with self._lock:
            pending = list(self._pending_tasks)
            start_index = self._task_index

        if pending and start_index < len(pending):
            self._execute_batch(pending, start_index)
            return

        try:
            tasks = self._fetch_task_list()
        except Exception as e:
            self._pause(f"获取任务列表失败: {e}")
            return

        if not tasks:
            self._log("[Scheduler] 暂无待执行任务")
            return

        self._log(f"[Scheduler] 获取到 {len(tasks)} 条任务")
        self._execute_batch(tasks, 0)

    def run(self):
        self._log("[Scheduler] ── 开始执行本轮任务 ──")
        self._run_pending_or_fetch()

        while self.running:
            if self.paused:
                self._resume_event.wait(timeout=1)
                if not self.running:
                    break
                if not self.paused:
                    self._log("[Scheduler] ── 恢复执行，从头获取任务 ──")
                    self._run_pending_or_fetch()
                continue

            waited = 0
            while self.running and not self.paused and waited < self.interval:
                time.sleep(1)
                waited += 1

            if self.running and not self.paused:
                self._log("[Scheduler] 距上轮已过 5 小时，开始新一轮任务")
                self._run_pending_or_fetch()
