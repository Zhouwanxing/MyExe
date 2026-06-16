import tkinter as tk
from tkinter import ttk, font as tkfont
from tkinter.scrolledtext import ScrolledText
import pystray
from PIL import Image
import threading
import sys
import os

# 尝试不同的导入方式以兼容 PyInstaller 打包
try:
    from server import FastAPIServer
    from proxy_server import ProxyServer
    from scheduler import SimpleScheduler
    from utils.time_utils import current_datetime_str
    from utils.config_loader import Config
except ImportError:
    from MyExe.server import FastAPIServer
    from MyExe.proxy_server import ProxyServer
    from MyExe.scheduler import SimpleScheduler
    from MyExe.utils.time_utils import current_datetime_str
    from MyExe.utils.config_loader import Config


# ── 浅色配色 ──────────────────────────────────────────────
COLORS = {
    "bg":           "#f0f2f5",
    "surface":      "#ffffff",
    "surface_alt":  "#ffffff",
    "border":       "#e2e6ed",
    "accent":       "#4f86f7",
    "accent_hover": "#3b72e8",
    "accent_light": "#e8f0fe",
    "success":      "#34a853",
    "success_light":"#e6f4ea",
    "warning":      "#e37400",
    "danger":       "#d93025",
    "danger_light": "#fce8e6",
    "text":         "#1f2937",
    "text_dim":     "#6b7280",
    "log_bg":       "#fafbfc",
    "log_fg":       "#374151",
    "btn_bg":       "#ffffff",
    "btn_hover":    "#eef1f6",
    "btn_active":   "#e2e7ef",
    "btn_border":   "#d8dce3",
    "btn_disabled": "#f3f4f6",
}


class RoundedButton(tk.Frame):
    """统一圆角的浅色按钮。"""

    RADIUS = 10
    PADX = 18
    PADY = 9
    FONT = ("Segoe UI", 10)

    VARIANTS = {
        "primary": ("#e8f0fe", "#d2e3fc", "#1967d2", "#4f86f7"),
        "success": ("#e6f4ea", "#cce7d4", "#137333", "#34a853"),
        "ghost":   ("#ffffff", "#eef1f6", "#374151", "#d8dce3"),
        "danger":  ("#fce8e6", "#f5c6c2", "#c5221f", "#f5a8a2"),
    }

    def __init__(self, parent, text="", command=None, variant="ghost", bg=None, **kwargs):
        super().__init__(parent, bg=bg or COLORS["bg"])
        self._text = text
        self._command = command
        self._variant = variant
        self._state = "normal"
        self._hover = False

        self.canvas = tk.Canvas(
            self, highlightthickness=0, borderwidth=0,
            bg=bg or COLORS["bg"], cursor="hand2",
        )
        self.canvas.pack()
        self._redraw()
        self._bind_events()

    def _colors(self):
        bg, hover, fg, border = self.VARIANTS[self._variant]
        if self._state == "disabled":
            return COLORS["btn_disabled"], COLORS["btn_disabled"], COLORS["text_dim"], COLORS["border"]
        if self._hover:
            return hover, hover, fg, border
        return bg, hover, fg, border

    def _measure(self):
        f = tkfont.Font(font=self.FONT)
        w = f.measure(self._text) + self.PADX * 2
        h = f.metrics("linespace") + self.PADY * 2
        return max(w, 80), max(h, 36)

    def _round_rect(self, x1, y1, x2, y2, r, fill, outline):
        points = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]
        return self.canvas.create_polygon(points, smooth=True, fill=fill, outline=outline, width=1)

    def _redraw(self):
        self.canvas.delete("all")
        w, h = self._measure()
        self.canvas.configure(width=w, height=h)
        bg, _, fg, border = self._colors()
        self._round_rect(1, 1, w - 1, h - 1, self.RADIUS, bg, border)
        self.canvas.create_text(w // 2, h // 2, text=self._text, fill=fg, font=self.FONT)

    def _bind_events(self):
        for seq, fn in [
            ("<Enter>", lambda e: self._set_hover(True)),
            ("<Leave>", lambda e: self._set_hover(False)),
            ("<Button-1>", self._on_click),
        ]:
            self.canvas.bind(seq, fn)
            self.bind(seq, fn)

    def _set_hover(self, hover):
        if self._state == "disabled":
            return
        self._hover = hover
        self._redraw()

    def _on_click(self, _event=None):
        if self._state == "disabled" or not self._command:
            return
        self._command()

    def configure(self, cnf=None, **kwargs):
        if cnf:
            kwargs.update(cnf)
        if "text" in kwargs:
            self._text = kwargs.pop("text")
        if "state" in kwargs:
            self._state = kwargs.pop("state")
            self.canvas.configure(cursor="arrow" if self._state == "disabled" else "hand2")
        if "command" in kwargs:
            self._command = kwargs.pop("command")
        if "variant" in kwargs:
            self._variant = kwargs.pop("variant")
        self._redraw()

    config = configure


class MyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MyExe 控制台")
        self.root.geometry("960x580")
        self.root.minsize(720, 420)
        self.root.configure(bg=COLORS["bg"])

        self.tray_icon = None
        self.tray_thread = None
        self.is_minimized = False

        self._setup_styles()
        self._build_header()
        self._build_status_bar()
        self._build_toolbar()
        self._build_log_area()
        self._build_footer()

        self._resource_path = self._make_resource_path()
        self._setup_window_icon()

        self.server = FastAPIServer(port=Config.get("server.port"), gui_logger=self.print_to_gui)
        self.proxy = ProxyServer(gui_logger=self.print_to_gui)
        self.scheduler = SimpleScheduler(interval=60 * 60, gui_logger=self.print_to_gui)
        self._proxy_dialog = None

        self._update_port_label()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.setup_system_tray()

    # ── 样式 ──────────────────────────────────────────────

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", background=COLORS["bg"], foreground=COLORS["text"],
                        font=("Segoe UI", 10))
        style.configure("TFrame", background=COLORS["bg"])
        style.configure("Surface.TFrame", background=COLORS["surface"])
        style.configure("Header.TFrame", background=COLORS["surface"])

        style.configure("Title.TLabel",
                        background=COLORS["surface"], foreground=COLORS["text"],
                        font=("Segoe UI", 16, "bold"))
        style.configure("Subtitle.TLabel",
                        background=COLORS["surface"], foreground=COLORS["text_dim"],
                        font=("Segoe UI", 9))
        style.configure("Status.TLabel",
                        background=COLORS["surface_alt"], foreground=COLORS["text_dim"],
                        font=("Segoe UI", 9))
        style.configure("StatusValue.TLabel",
                        background=COLORS["surface_alt"], foreground=COLORS["text"],
                        font=("Segoe UI", 9, "bold"))
        style.configure("Footer.TLabel",
                        background=COLORS["surface"], foreground=COLORS["text_dim"],
                        font=("Segoe UI", 8))
        style.configure("LogTitle.TLabel",
                        background=COLORS["bg"], foreground=COLORS["text_dim"],
                        font=("Segoe UI", 9))

    def _make_btn(self, parent, text, command, variant="ghost"):
        return RoundedButton(parent, text=text, command=command, variant=variant, bg=COLORS["bg"])

    # ── 布局构建 ──────────────────────────────────────────

    def _build_header(self):
        header = ttk.Frame(self.root, style="Header.TFrame", padding=(20, 16))
        header.pack(fill=tk.X)

        left = ttk.Frame(header, style="Header.TFrame")
        left.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(left, text="MyExe 控制台", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(left, text="HTTP 服务 · 端口转发 · 定时任务 · 系统托盘", style="Subtitle.TLabel").pack(anchor=tk.W, pady=(2, 0))

        self.port_label = ttk.Label(header, text="", style="Subtitle.TLabel")
        self.port_label.pack(side=tk.RIGHT, anchor=tk.NE)

    def _build_status_bar(self):
        bar = ttk.Frame(self.root, padding=(20, 0, 20, 12))
        bar.pack(fill=tk.X)

        self.server_status_frame = self._status_card(bar, "HTTP 服务", "已停止", COLORS["text_dim"])
        self.server_status_frame.pack(side=tk.LEFT, padx=(0, 10))

        self.scheduler_status_frame = self._status_card(bar, "定时任务", "已停止", COLORS["text_dim"])
        self.scheduler_status_frame.pack(side=tk.LEFT, padx=(0, 10))

        self.proxy_status_frame = self._status_card(bar, "端口转发", "未配置", COLORS["text_dim"])
        self.proxy_status_frame.pack(side=tk.LEFT)

    def _status_card(self, parent, title, value, dot_color):
        card = tk.Frame(parent, bg=COLORS["surface"], highlightbackground=COLORS["border"],
                        highlightthickness=1, padx=14, pady=10)
        inner = tk.Frame(card, bg=COLORS["surface"])
        inner.pack()

        dot = tk.Label(inner, text="●", bg=COLORS["surface"], fg=dot_color,
                       font=("Segoe UI", 8))
        dot.pack(side=tk.LEFT, padx=(0, 6))

        text_frame = tk.Frame(inner, bg=COLORS["surface"])
        text_frame.pack(side=tk.LEFT)

        tk.Label(text_frame, text=title, bg=COLORS["surface"], fg=COLORS["text_dim"],
                 font=("Segoe UI", 8)).pack(anchor=tk.W)
        value_label = tk.Label(text_frame, text=value, bg=COLORS["surface"], fg=COLORS["text"],
                               font=("Segoe UI", 10, "bold"))
        value_label.pack(anchor=tk.W)

        card.dot = dot
        card.value_label = value_label
        return card

    def _set_status(self, card, running, running_text, stopped_text):
        if running_text == "停止中":
            card.dot.configure(fg=COLORS["warning"])
            card.value_label.configure(text=running_text, fg=COLORS["warning"])
        elif running:
            card.dot.configure(fg=COLORS["success"])
            card.value_label.configure(text=running_text, fg=COLORS["success"])
        else:
            card.dot.configure(fg=COLORS["text_dim"])
            card.value_label.configure(text=stopped_text, fg=COLORS["text_dim"])

    def _build_toolbar(self):
        toolbar = tk.Frame(self.root, bg=COLORS["bg"], padx=20, pady=0)
        toolbar.pack(fill=tk.X, pady=(0, 12))

        self.server_btn = self._make_btn(toolbar, "▶  启动 HTTP 服务", self.toggle_server, "success")
        self.server_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.scheduler_btn = self._make_btn(toolbar, "▶  启动定时任务", self.toggle_scheduler, "primary")
        self.scheduler_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.proxy_btn = self._make_btn(toolbar, "⇄  端口转发", self.open_proxy_dialog, "primary")
        self.proxy_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.minimize_btn = self._make_btn(toolbar, "⬇  最小化到托盘", self.minimize_to_tray, "ghost")
        self.minimize_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.exit_btn = self._make_btn(toolbar, "✕  退出", self.exit_app, "danger")
        self.exit_btn.pack(side=tk.RIGHT)

    def _build_log_area(self):
        wrapper = ttk.Frame(self.root, padding=(20, 0, 20, 8))
        wrapper.pack(fill=tk.BOTH, expand=True)

        ttk.Label(wrapper, text="运行日志", style="LogTitle.TLabel").pack(anchor=tk.W, pady=(0, 6))

        log_frame = tk.Frame(wrapper, bg=COLORS["border"], padx=1, pady=1)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = ScrolledText(
            log_frame,
            state="disabled",
            wrap=tk.WORD,
            bg=COLORS["log_bg"],
            fg=COLORS["log_fg"],
            insertbackground=COLORS["text"],
            selectbackground=COLORS["accent_light"],
            selectforeground=COLORS["text"],
            font=("Consolas", 10),
            relief=tk.FLAT,
            padx=12,
            pady=10,
            borderwidth=0,
            highlightthickness=0,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.log_text.tag_configure("timestamp", foreground=COLORS["text_dim"])
        self.log_text.tag_configure("info", foreground=COLORS["log_fg"])
        self.log_text.tag_configure("warn", foreground=COLORS["warning"])
        self.log_text.tag_configure("error", foreground=COLORS["danger"])

    def _build_footer(self):
        footer = ttk.Frame(self.root, style="Header.TFrame", padding=(20, 8))
        footer.pack(fill=tk.X, side=tk.BOTTOM)

        self.footer_label = ttk.Label(footer, text="就绪", style="Footer.TLabel")
        self.footer_label.pack(side=tk.LEFT)

        ttk.Label(footer, text="关闭窗口将最小化到系统托盘", style="Footer.TLabel").pack(side=tk.RIGHT)

    def _update_port_label(self):
        port = Config.get("server.port")
        self.port_label.configure(text=f"端口 {port}")

    # ── 资源与图标 ────────────────────────────────────────

    def _make_resource_path(self):
        def _resource_path(relative_path):
            if hasattr(sys, "_MEIPASS"):
                base_path = sys._MEIPASS  # type: ignore[attr-defined]
            elif getattr(sys, "frozen", False):
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            return os.path.join(base_path, relative_path)
        return _resource_path

    def _setup_window_icon(self):
        try:
            icon_paths = [
                self._resource_path("jerry.ico"),
                self._resource_path("icon.ico"),
                self._resource_path("jerry.png"),
                self._resource_path("icon.png"),
            ]
            for icon_path in icon_paths:
                if not os.path.exists(icon_path):
                    continue
                if icon_path.lower().endswith(".ico"):
                    self.root.iconbitmap(icon_path)
                    return
                if icon_path.lower().endswith(".png"):
                    from PIL import ImageTk
                    img = Image.open(icon_path).resize((32, 32), Image.Resampling.LANCZOS)
                    self.icon_photo = ImageTk.PhotoImage(img)
                    self.root.iconphoto(False, self.icon_photo)
                    return
            self.print_to_gui("警告: 未找到可用的图标文件，使用默认图标", tag="warn")
        except Exception as e:
            self.print_to_gui(f"设置窗口图标失败: {e}", tag="error")

    # ── 日志输出 ──────────────────────────────────────────

    def print_to_gui(self, msg, tag="info"):
        if tag not in ("timestamp", "info", "warn", "error"):
            lower = str(msg).lower()
            if "警告" in str(msg) or "warn" in lower:
                tag = "warn"
            elif "失败" in str(msg) or "错误" in str(msg) or "error" in lower:
                tag = "error"
            else:
                tag = "info"

        ts = current_datetime_str()
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, f"[{ts}] ", "timestamp")
        self.log_text.insert(tk.END, f"{msg}\n", tag)
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")
        self.footer_label.configure(text=str(msg)[:80])

    # ── 服务控制 ──────────────────────────────────────────

    def toggle_server(self):
        if self.server.running:
            self.server_btn.configure(state="disabled", text="⏳  停止中...")
            self._set_status(self.server_status_frame, False, "停止中", "已停止")

            def _stop():
                self.server.stop()
                self.root.after(0, self._on_server_stopped)

            threading.Thread(target=_stop, daemon=True).start()
        else:
            self.server.start()
            self.server_btn.configure(text="⏸  暂停 HTTP 服务")
            self._set_status(self.server_status_frame, True, "运行中", "已停止")

    def _on_server_stopped(self):
        self.server_btn.configure(state="normal", text="▶  启动 HTTP 服务")
        self._set_status(self.server_status_frame, False, "运行中", "已停止")

    def toggle_scheduler(self):
        if self.scheduler.running:
            self.scheduler.stop()
            self.scheduler_btn.configure(text="▶  启动定时任务")
            self._set_status(self.scheduler_status_frame, False, "运行中", "已停止")
        else:
            self.scheduler.start()
            self.scheduler_btn.configure(text="⏸  暂停定时任务")
            self._set_status(self.scheduler_status_frame, True, "运行中", "已停止")

    # ── 端口转发 ──────────────────────────────────────────

    def _update_proxy_status(self, running=False, text=None):
        if text is None:
            if running and self.proxy.target_url:
                text = f":{self.proxy.port} → 运行中"
            elif self.proxy.target_url:
                text = f":{self.proxy.port} → 已停止"
            else:
                text = "未配置"
        self._set_status(self.proxy_status_frame, running, text, text if not running else "已停止")

    def open_proxy_dialog(self):
        if self._proxy_dialog and self._proxy_dialog.winfo_exists():
            self._proxy_dialog.lift()
            self._proxy_dialog.focus_force()
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("端口转发")
        dialog.configure(bg=COLORS["bg"])
        dialog.geometry("480x260")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        self._proxy_dialog = dialog

        default_port = self.proxy.port if (self.proxy.target_url or self.proxy.running) else 10002
        default_target = self.proxy.target_url or Config.get("server.baseUrl1", "http://127.0.0.1:8080")

        frame = tk.Frame(dialog, bg=COLORS["bg"], padx=24, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            frame, text="将本地端口的 HTTP 请求转发到目标接口地址",
            bg=COLORS["bg"], fg=COLORS["text_dim"], font=("Segoe UI", 9),
        ).pack(anchor=tk.W, pady=(0, 16))

        port_row = tk.Frame(frame, bg=COLORS["bg"])
        port_row.pack(fill=tk.X, pady=(0, 12))
        tk.Label(port_row, text="监听端口", bg=COLORS["bg"], fg=COLORS["text"],
                 font=("Segoe UI", 10), width=10, anchor=tk.W).pack(side=tk.LEFT)
        port_var = tk.StringVar(value=str(default_port))
        port_entry = tk.Entry(
            port_row, textvariable=port_var, font=("Segoe UI", 10),
            bg=COLORS["surface"], fg=COLORS["text"], relief=tk.FLAT,
            highlightbackground=COLORS["border"], highlightthickness=1,
        )
        port_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)

        target_row = tk.Frame(frame, bg=COLORS["bg"])
        target_row.pack(fill=tk.X, pady=(0, 20))
        tk.Label(target_row, text="目标地址", bg=COLORS["bg"], fg=COLORS["text"],
                 font=("Segoe UI", 10), width=10, anchor=tk.W).pack(side=tk.LEFT)
        target_var = tk.StringVar(value=default_target)
        target_entry = tk.Entry(
            target_row, textvariable=target_var, font=("Segoe UI", 10),
            bg=COLORS["surface"], fg=COLORS["text"], relief=tk.FLAT,
            highlightbackground=COLORS["border"], highlightthickness=1,
        )
        target_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)

        btn_row = tk.Frame(frame, bg=COLORS["bg"])
        btn_row.pack(fill=tk.X)

        def _parse_port():
            try:
                port = int(port_var.get().strip())
                if not (1 <= port <= 65535):
                    raise ValueError
                return port
            except ValueError:
                self.print_to_gui("端口无效，请输入 1-65535 之间的数字", tag="warn")
                return None

        def _parse_target():
            target = target_var.get().strip().rstrip("/")
            if not target.startswith(("http://", "https://")):
                self.print_to_gui("目标地址需以 http:// 或 https:// 开头", tag="warn")
                return None
            return target

        def _start_proxy():
            port = _parse_port()
            target = _parse_target()
            if port is None or target is None:
                return

            if self.server.running and port == self.server.port:
                self.print_to_gui(f"端口 {port} 已被 HTTP 服务占用", tag="warn")
                return

            if self.proxy.running:
                self.print_to_gui("请先停止当前端口转发", tag="warn")
                return

            self.proxy.configure(port, target)
            if self.proxy.start():
                start_btn.configure(state="disabled")
                stop_btn.configure(state="normal")
                port_entry.configure(state="disabled")
                target_entry.configure(state="disabled")
                self._update_proxy_status(running=True)

        def _stop_proxy():
            if not self.proxy.running:
                return

            stop_btn.configure(state="disabled", text="停止中...")

            def _do_stop():
                self.proxy.stop()
                self.root.after(0, _on_stopped)

            threading.Thread(target=_do_stop, daemon=True).start()

        def _on_stopped():
            stop_btn.configure(state="normal", text="停止转发")
            start_btn.configure(state="normal")
            port_entry.configure(state="normal")
            target_entry.configure(state="normal")
            self._update_proxy_status(running=False)

        start_btn = RoundedButton(btn_row, text="启动转发", command=_start_proxy, variant="success", bg=COLORS["bg"])
        start_btn.pack(side=tk.LEFT, padx=(0, 8))

        stop_btn = RoundedButton(btn_row, text="停止转发", command=_stop_proxy, variant="danger", bg=COLORS["bg"])
        stop_btn.pack(side=tk.LEFT, padx=(0, 8))

        close_btn = RoundedButton(btn_row, text="关闭", command=dialog.destroy, variant="ghost", bg=COLORS["bg"])
        close_btn.pack(side=tk.RIGHT)

        if self.proxy.running:
            start_btn.configure(state="disabled")
            port_entry.configure(state="disabled")
            target_entry.configure(state="disabled")
        else:
            stop_btn.configure(state="disabled")

        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)

    # ── 系统托盘 ──────────────────────────────────────────

    def setup_system_tray(self):
        try:
            icon_paths = [
                self._resource_path("jerry.png"),
                self._resource_path("jerry.ico"),
                self._resource_path("icon.ico"),
                self._resource_path("icon.png"),
            ]

            image = None
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    try:
                        image = Image.open(icon_path)
                        if image.mode != "RGBA":
                            image = image.convert("RGBA")
                        image = image.resize((32, 32), Image.Resampling.LANCZOS)
                        break
                    except Exception as e:
                        self.print_to_gui(f"加载图标失败 {icon_path}: {e}", tag="error")

            if image is None:
                image = Image.new("RGB", (64, 64), color="#7aa2f7")
                self.print_to_gui("使用默认图标作为系统托盘图标", tag="warn")

            menu = pystray.Menu(
                pystray.MenuItem("显示窗口", self.show_window, default=True),
                pystray.MenuItem("启动 HTTP 服务", self.toggle_server_from_tray),
                pystray.MenuItem("启动定时任务", self.toggle_scheduler_from_tray),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出", self.quit_app),
            )

            self.tray_image = image
            self.tray_icon = pystray.Icon("MyExe", self.tray_image, "MyExe 控制台", menu)
            self.tray_thread = threading.Thread(target=self.run_tray, daemon=True)
            self.tray_thread.start()
        except Exception as e:
            self.print_to_gui(f"系统托盘设置失败: {e}", tag="error")

    def run_tray(self):
        try:
            self.tray_icon.run()
        except Exception as e:
            self.print_to_gui(f"系统托盘运行错误: {e}", tag="error")

    def show_window(self, icon=None, item=None):
        self.root.after(0, self._show_window)

    def _show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.is_minimized = False

    def minimize_to_tray(self):
        self.root.withdraw()
        self.is_minimized = True
        self.print_to_gui("程序已最小化到系统托盘")

    def toggle_server_from_tray(self, icon=None, item=None):
        self.root.after(0, self.toggle_server)

    def toggle_scheduler_from_tray(self, icon=None, item=None):
        self.root.after(0, self.toggle_scheduler)

    def on_closing(self):
        if self.is_minimized:
            self.root.withdraw()
        else:
            self.minimize_to_tray()

    def quit_app(self, icon=None, item=None):
        self.root.after(0, self._quit_app)

    def _quit_app(self):
        if self.tray_icon:
            self.tray_icon.stop()
        self.exit_app()

    def exit_app(self):
        if self.server.running:
            self.server.stop()
        if self.proxy.running:
            self.proxy.stop()
        if self.scheduler.running:
            self.scheduler.stop()
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()


def run():
    root = tk.Tk()
    MyApp(root)
    root.mainloop()
