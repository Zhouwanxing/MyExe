import threading
import time
from datetime import datetime

try:
    from macro_engine import MacroPlayer
    from macro_storage import list_macros, load_macro
    from macro_api import MacroApiError
except ImportError:
    from MyExe.macro_engine import MacroPlayer
    from MyExe.macro_storage import list_macros, load_macro
    from MyExe.macro_api import MacroApiError


class MacroScheduler:
    """按宏配置中的 schedule 字段定时执行录制。"""

    CHECK_INTERVAL = 30

    def __init__(self, gui_logger=None):
        self.gui_logger = gui_logger
        self.running = False
        self.thread = None
        self.player = MacroPlayer(logger=gui_logger)
        self._lock = threading.Lock()
        self._executing = False

    def _log(self, msg, tag="info"):
        if self.gui_logger:
            self.gui_logger(msg, tag=tag)

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self._log("[MacroScheduler] 定时执行已启动")

    def stop(self):
        self.running = False
        self._log("[MacroScheduler] 定时执行已停止")

    def execute_now(self, macro_id, callback=None):
        """立即在后台线程执行指定宏。"""
        def _run():
            with self._lock:
                if self._executing:
                    self._log("[Macro] 已有宏正在执行，请稍候", tag="warn")
                    if callback:
                        callback(False)
                    return
                self._executing = True
            try:
                macro = load_macro(macro_id)
                if not macro:
                    self._log(f"[Macro] 未找到录制: {macro_id}", tag="warn")
                    ok = False
                else:
                    ok = self.player.play(macro)
            finally:
                with self._lock:
                    self._executing = False
                if callback:
                    callback(ok)

        threading.Thread(target=_run, daemon=True).start()

    def _should_run(self, macro, now):
        schedule = macro.get("schedule") or {}
        if not schedule.get("enabled"):
            return False
        run_time = schedule.get("time", "")
        if not run_time or ":" not in run_time:
            return False
        try:
            hour, minute = map(int, run_time.split(":")[:2])
        except ValueError:
            return False
        if now.hour != hour or now.minute != minute:
            return False
        today = now.strftime("%Y-%m-%d")
        if schedule.get("last_run") == today:
            return False
        return True

    def _mark_run(self, macro):
        schedule = macro.setdefault("schedule", {})
        schedule["last_run"] = datetime.now().strftime("%Y-%m-%d")
        try:
            from macro_storage import save_macro
        except ImportError:
            from MyExe.macro_storage import save_macro
        try:
            save_macro(macro)
        except MacroApiError as e:
            self._log(f"[MacroScheduler] 更新执行记录失败: {e}", tag="warn")

    def _run(self):
        while self.running:
            now = datetime.now()
            try:
                macros = list_macros()
            except MacroApiError as e:
                self._log(f"[MacroScheduler] 获取录制列表失败: {e}", tag="warn")
                time.sleep(self.CHECK_INTERVAL)
                continue
            for macro in macros:
                if not self._should_run(macro, now):
                    continue
                with self._lock:
                    if self._executing:
                        continue
                    self._executing = True
                name = macro.get("name", macro.get("id", ""))
                self._log(f"[MacroScheduler] 定时触发: {name}")
                try:
                    self.player.play(macro)
                    self._mark_run(macro)
                finally:
                    with self._lock:
                        self._executing = False
            time.sleep(self.CHECK_INTERVAL)
