import tkinter as tk
from tkinter import ttk, font as tkfont
from tkinter.scrolledtext import ScrolledText
import pystray
from PIL import Image
import threading
import sys
import os
import time
import uuid

# 尝试不同的导入方式以兼容 PyInstaller 打包
try:
    from server import FastAPIServer
    from proxy_server import ProxyServer
    from scheduler import SimpleScheduler
    from macro_engine import MacroRecorder, MacroPlayer, open_browser
    from macro_storage import list_macros, save_macro, delete_macro, load_macro
    from macro_api import MacroApiError
    from macro_scheduler import MacroScheduler
    from utils.time_utils import current_datetime_str
    from utils.config_loader import Config
except ImportError:
    from MyExe.server import FastAPIServer
    from MyExe.proxy_server import ProxyServer
    from MyExe.scheduler import SimpleScheduler
    from MyExe.macro_engine import MacroRecorder, MacroPlayer, open_browser
    from MyExe.macro_storage import list_macros, save_macro, delete_macro, load_macro
    from MyExe.macro_api import MacroApiError
    from MyExe.macro_scheduler import MacroScheduler
    from MyExe.utils.time_utils import current_datetime_str
    from MyExe.utils.config_loader import Config


FONT_FAMILY = "Microsoft YaHei UI" if sys.platform == "win32" else "Segoe UI"


def _font(size=10, weight="normal"):
    if weight == "bold":
        return (FONT_FAMILY, size, "bold")
    return (FONT_FAMILY, size)


# ── 浅色配色 ──────────────────────────────────────────────
COLORS = {
    "bg":            "#e8ecf2",
    "surface":       "#ffffff",
    "surface_alt":   "#f7f9fc",
    "border":        "#dde3ec",
    "border_light":  "#eef2f7",
    "accent":        "#3b6cf4",
    "accent_hover":  "#2f5ad8",
    "accent_light":  "#e8efff",
    "success":       "#1e9e55",
    "success_light": "#e3f5eb",
    "warning":       "#d97706",
    "danger":        "#dc2626",
    "danger_light":  "#feecec",
    "text":          "#111827",
    "text_dim":      "#64748b",
    "log_bg":        "#f8fafc",
    "log_fg":        "#334155",
    "btn_bg":        "#ffffff",
    "btn_hover":     "#eef2f7",
    "btn_active":    "#e2e8f0",
    "btn_border":    "#cbd5e1",
    "btn_disabled":  "#f1f5f9",
}


def _panel(parent, bg=None):
    """带细边框的白色面板容器。"""
    wrap = tk.Frame(parent, bg=COLORS["bg"])
    panel = tk.Frame(
        wrap, bg=bg or COLORS["surface"],
        highlightbackground=COLORS["border"],
        highlightthickness=1,
    )
    panel.pack(fill=tk.BOTH, expand=True)
    wrap.panel = panel
    return wrap


class RoundedButton(tk.Frame):
    """统一圆角的浅色按钮。"""

    RADIUS = 10
    PADX = 18
    PADY = 9
    FONT = _font(10)

    VARIANTS = {
        "primary": ("#e8f0fe", "#d2e3fc", "#1967d2", "#4f86f7"),
        "success": ("#e6f4ea", "#cce7d4", "#137333", "#34a853"),
        "ghost":   ("#ffffff", "#eef1f6", "#374151", "#d8dce3"),
        "danger":  ("#fce8e6", "#f5c6c2", "#c5221f", "#f5a8a2"),
    }

    def __init__(self, parent, text="", command=None, variant="ghost", bg=None, compact=False, **kwargs):
        super().__init__(parent, bg=bg or COLORS["bg"])
        self._text = text
        self._command = command
        self._variant = variant
        self._state = "normal"
        self._hover = False
        self._compact = compact
        if compact:
            self._radius = 6
            self._padx = 10
            self._pady = 4
            self._btn_font = _font(9)
            self._min_w, self._min_h = 52, 28
        else:
            self._radius = self.RADIUS
            self._padx = self.PADX
            self._pady = self.PADY
            self._btn_font = self.FONT
            self._min_w, self._min_h = 80, 36

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
        f = tkfont.Font(font=self._btn_font)
        w = f.measure(self._text) + self._padx * 2
        h = f.metrics("linespace") + self._pady * 2
        return max(w, self._min_w), max(h, self._min_h)

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
        self._round_rect(1, 1, w - 1, h - 1, self._radius, bg, border)
        self.canvas.create_text(w // 2, h // 2, text=self._text, fill=fg, font=self._btn_font)

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
        self.root.geometry("1000x640")
        self.root.minsize(760, 480)
        self.root.configure(bg=COLORS["bg"])
        self._default_width = 1000
        self._default_height = 640

        self.tray_icon = None
        self.tray_thread = None
        self.is_minimized = False

        self._setup_styles()
        self._build_title_bar()
        self._build_status_bar()
        self._build_log_area()
        self._build_footer()

        self._resource_path = self._make_resource_path()
        self._setup_window_icon()

        self.server = FastAPIServer(port=Config.get("server.port"), gui_logger=self.print_to_gui)
        self.proxy = ProxyServer(gui_logger=self.print_to_gui)
        self.scheduler = SimpleScheduler(gui_logger=self.print_to_gui, on_pause=self._on_scheduler_paused)
        self.macro_recorder = MacroRecorder(logger=self.print_to_gui)
        self.macro_player = MacroPlayer(logger=self.print_to_gui)
        self.macro_scheduler = MacroScheduler(gui_logger=self.print_to_gui)
        self.macro_scheduler.start()
        self._proxy_dialog = None
        self._macro_dialog = None
        self._recording = False
        self._icon_flash_job = None
        self._icon_flash_step = 0
        self._tray_icon_normal = None
        self._tray_icon_alert = None
        self._tray_icon_flash = None
        self._window_title_normal = "MyExe 控制台"

        self._update_port_label()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.bind("<Unmap>", self._on_root_unmap)
        self.setup_system_tray()
        self._center_window(self._default_width, self._default_height)

    # ── 样式 ──────────────────────────────────────────────

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", background=COLORS["bg"], foreground=COLORS["text"], font=_font(10))
        style.configure("TFrame", background=COLORS["bg"])
        style.configure("Surface.TFrame", background=COLORS["surface"])
        style.configure("Header.TFrame", background=COLORS["surface"])

        style.configure("Title.TLabel",
                        background=COLORS["surface"], foreground=COLORS["text"],
                        font=_font(18, "bold"))
        style.configure("Subtitle.TLabel",
                        background=COLORS["surface"], foreground=COLORS["text_dim"],
                        font=_font(9))
        style.configure("Status.TLabel",
                        background=COLORS["surface_alt"], foreground=COLORS["text_dim"],
                        font=_font(9))
        style.configure("StatusValue.TLabel",
                        background=COLORS["surface_alt"], foreground=COLORS["text"],
                        font=_font(9, "bold"))
        style.configure("Footer.TLabel",
                        background=COLORS["surface"], foreground=COLORS["text_dim"],
                        font=_font(8))
        style.configure("LogTitle.TLabel",
                        background=COLORS["surface"], foreground=COLORS["text"],
                        font=_font(10, "bold"))
        style.configure("LogHint.TLabel",
                        background=COLORS["surface"], foreground=COLORS["text_dim"],
                        font=_font(8))

        RoundedButton.FONT = _font(10)

    def _make_btn(self, parent, text, command, variant="ghost", bg=None, compact=False):
        surface = bg
        if surface is None:
            try:
                surface = parent.cget("bg")
            except tk.TclError:
                surface = COLORS["bg"]
        return RoundedButton(
            parent, text=text, command=command, variant=variant, bg=surface, compact=compact,
        )

    # ── 布局构建 ──────────────────────────────────────────

    def _build_title_bar(self):
        title_bar = tk.Frame(self.root, bg=COLORS["surface"], padx=6, pady=4)
        title_bar.pack(fill=tk.X, side=tk.TOP)
        self._title_bar = title_bar

        right = tk.Frame(title_bar, bg=COLORS["surface"])
        right.pack(side=tk.RIGHT)

        self.port_badge = tk.Frame(
            right, bg=COLORS["accent_light"],
            highlightbackground=COLORS["accent"], highlightthickness=1,
            padx=8, pady=2,
        )
        self.port_badge.pack(side=tk.RIGHT, padx=(8, 4))

        self.port_label = tk.Label(
            self.port_badge, text="", bg=COLORS["accent_light"], fg=COLORS["accent"],
            font=_font(9, "bold"),
        )
        self.port_label.pack()

        emblem = tk.Label(
            title_bar, text="⚡", bg=COLORS["accent_light"], fg=COLORS["accent"],
            font=_font(11), padx=5, pady=1,
        )
        emblem.pack(side=tk.LEFT, padx=(2, 6))
        self.header_emblem = emblem

        tk.Frame(title_bar, bg=COLORS["border"], width=1).pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8), pady=3)

        btn_row = tk.Frame(title_bar, bg=COLORS["surface"])
        btn_row.pack(side=tk.LEFT)

        self.server_btn = self._make_btn(btn_row, "▶ HTTP", self.toggle_server, "success", compact=True)
        self.server_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.scheduler_btn = self._make_btn(btn_row, "▶ 定时", self.toggle_scheduler, "primary", compact=True)
        self.scheduler_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.proxy_btn = self._make_btn(btn_row, "⇄ 转发", self.open_proxy_dialog, "primary", compact=True)
        self.proxy_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.macro_btn = self._make_btn(btn_row, "⏺ 录制", self.open_macro_dialog, "primary", compact=True)
        self.macro_btn.pack(side=tk.LEFT)

        tk.Frame(self.root, bg=COLORS["border"], height=1).pack(fill=tk.X)

    def _build_status_bar(self):
        bar = tk.Frame(self.root, bg=COLORS["bg"])
        bar.pack(fill=tk.X, padx=24, pady=(16, 0))
        for col in range(3):
            bar.columnconfigure(col, weight=1, uniform="status")

        self.server_status_frame = self._status_card(bar, "HTTP 服务", "已停止", COLORS["text_dim"])
        self.server_status_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.scheduler_status_frame = self._status_card(bar, "定时任务", "已停止", COLORS["text_dim"])
        self.scheduler_status_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 8))

        self.proxy_status_frame = self._status_card(bar, "端口转发", "未配置", COLORS["text_dim"])
        self.proxy_status_frame.grid(row=0, column=2, sticky="nsew")

    def _status_card(self, parent, title, value, accent_color):
        card = tk.Frame(
            parent, bg=COLORS["surface"],
            highlightbackground=COLORS["border"], highlightthickness=1,
        )

        accent = tk.Frame(card, bg=accent_color, width=4)
        accent.pack(side=tk.LEFT, fill=tk.Y)

        body = tk.Frame(card, bg=COLORS["surface"], padx=16, pady=14)
        body.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        top = tk.Frame(body, bg=COLORS["surface"])
        top.pack(fill=tk.X)

        dot = tk.Label(top, text="●", bg=COLORS["surface"], fg=accent_color, font=_font(7))
        dot.pack(side=tk.LEFT, padx=(0, 6))

        tk.Label(
            top, text=title, bg=COLORS["surface"], fg=COLORS["text_dim"], font=_font(8),
        ).pack(side=tk.LEFT)

        value_label = tk.Label(
            body, text=value, bg=COLORS["surface"], fg=COLORS["text"],
            font=_font(11, "bold"), anchor=tk.W,
        )
        value_label.pack(anchor=tk.W, pady=(6, 0))

        card.accent = accent
        card.dot = dot
        card.value_label = value_label
        return card

    def _set_status(self, card, running, running_text, stopped_text):
        if running_text == "停止中":
            color = COLORS["warning"]
            card.dot.configure(fg=color)
            card.accent.configure(bg=color)
            card.value_label.configure(text=running_text, fg=color)
        elif running:
            color = COLORS["success"]
            card.dot.configure(fg=color)
            card.accent.configure(bg=color)
            card.value_label.configure(text=running_text, fg=color)
        else:
            color = COLORS["text_dim"]
            card.dot.configure(fg=color)
            card.accent.configure(bg=color)
            card.value_label.configure(text=stopped_text, fg=COLORS["text_dim"])

    def _build_log_area(self):
        wrap = _panel(self.root)
        wrap.pack(fill=tk.BOTH, expand=True, padx=24, pady=(14, 12))

        panel = wrap.panel

        log_header = tk.Frame(panel, bg=COLORS["surface"], padx=16)
        log_header.pack(fill=tk.X, pady=(12, 8))

        tk.Label(
            log_header, text="运行日志", bg=COLORS["surface"], fg=COLORS["text"], font=_font(10, "bold"),
        ).pack(side=tk.LEFT)

        tk.Label(
            log_header, text="实时输出服务与任务状态",
            bg=COLORS["surface"], fg=COLORS["text_dim"], font=_font(8),
        ).pack(side=tk.LEFT, padx=(10, 0))

        self.clear_log_btn = self._make_btn(log_header, "清空", self._clear_log, "ghost")
        self.clear_log_btn.pack(side=tk.RIGHT)

        tk.Frame(panel, bg=COLORS["border_light"], height=1).pack(fill=tk.X)

        log_body = tk.Frame(panel, bg=COLORS["log_bg"], padx=1, pady=1)
        log_body.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        self.log_text = ScrolledText(
            log_body,
            state="disabled",
            wrap=tk.WORD,
            bg=COLORS["log_bg"],
            fg=COLORS["log_fg"],
            insertbackground=COLORS["text"],
            selectbackground=COLORS["accent_light"],
            selectforeground=COLORS["text"],
            font=("Cascadia Mono", 10) if sys.platform == "win32" else ("Consolas", 10),
            relief=tk.FLAT,
            padx=14,
            pady=12,
            borderwidth=0,
            highlightthickness=0,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.log_text.tag_configure("timestamp", foreground=COLORS["text_dim"])
        self.log_text.tag_configure("info", foreground=COLORS["log_fg"])
        self.log_text.tag_configure("warn", foreground=COLORS["warning"])
        self.log_text.tag_configure("error", foreground=COLORS["danger"])
        self.log_text.tag_configure("success", foreground=COLORS["success"])

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")
        self.footer_label.configure(text="日志已清空")

    def _build_footer(self):
        tk.Frame(self.root, bg=COLORS["border"], height=1).pack(fill=tk.X, side=tk.BOTTOM)

        footer = tk.Frame(self.root, bg=COLORS["surface"], padx=24, pady=10)
        footer.pack(fill=tk.X, side=tk.BOTTOM)

        status_dot = tk.Label(footer, text="●", bg=COLORS["surface"], fg=COLORS["success"], font=_font(7))
        status_dot.pack(side=tk.LEFT, padx=(0, 6))

        self.footer_label = tk.Label(
            footer, text="就绪", bg=COLORS["surface"], fg=COLORS["text_dim"], font=_font(8),
        )
        self.footer_label.pack(side=tk.LEFT)

        tk.Label(
            footer, text="关闭窗口将最小化到系统托盘",
            bg=COLORS["surface"], fg=COLORS["text_dim"], font=_font(8),
        ).pack(side=tk.RIGHT)

    def _update_port_label(self):
        port = Config.get("server.port")
        self.port_label.configure(text=f"监听端口  {port}")

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
        if tag not in ("timestamp", "info", "warn", "error", "success"):
            lower = str(msg).lower()
            if "警告" in str(msg) or "warn" in lower:
                tag = "warn"
            elif "失败" in str(msg) or "错误" in str(msg) or "error" in lower:
                tag = "error"
            elif "完成" in str(msg) or "success" in lower:
                tag = "success"
            else:
                tag = "info"

        def _append():
            ts = current_datetime_str()
            self.log_text.configure(state="normal")
            self.log_text.insert(tk.END, f"[{ts}] ", "timestamp")
            self.log_text.insert(tk.END, f"{msg}\n", tag)
            self.log_text.see(tk.END)
            self.log_text.configure(state="disabled")
            self.footer_label.configure(text=str(msg)[:80])

        if threading.current_thread() is threading.main_thread():
            _append()
        else:
            self.root.after(0, _append)

    # ── 服务控制 ──────────────────────────────────────────

    def toggle_server(self):
        if self.server.running:
            self.server_btn.configure(state="disabled", text="⏳ …")
            self._set_status(self.server_status_frame, False, "停止中", "已停止")

            def _stop():
                self.server.stop()
                self.root.after(0, self._on_server_stopped)

            threading.Thread(target=_stop, daemon=True).start()
        else:
            self.server.start()
            self.server_btn.configure(text="⏸ HTTP")
            self._set_status(self.server_status_frame, True, "运行中", "已停止")
            self.print_to_gui("[Server] HTTP 服务已启动")
            if not self.scheduler.running:
                self.scheduler.start()
                self._update_scheduler_ui()

    def _on_server_stopped(self):
        self.server_btn.configure(state="normal", text="▶ HTTP")
        self._set_status(self.server_status_frame, False, "运行中", "已停止")

    def _update_scheduler_ui(self):
        if self.scheduler.running and self.scheduler.paused:
            self.scheduler_btn.configure(text="▶ 恢复", variant="success")
            self._set_scheduler_status_paused()
        elif self.scheduler.running:
            self.scheduler_btn.configure(text="⏸ 定时", variant="primary")
            self._set_status(self.scheduler_status_frame, True, "运行中", "已停止")
        else:
            self.scheduler_btn.configure(text="▶ 定时", variant="primary")
            self._set_status(self.scheduler_status_frame, False, "运行中", "已停止")

    def _set_scheduler_status_paused(self):
        color = COLORS["warning"]
        card = self.scheduler_status_frame
        card.dot.configure(fg=color)
        card.accent.configure(bg=color)
        card.value_label.configure(text="已暂停", fg=color)

    def _on_scheduler_paused(self, reason):
        self.root.after(0, lambda: self._handle_scheduler_paused(reason))

    def _handle_scheduler_paused(self, reason):
        self._update_scheduler_ui()
        self.print_to_gui(f"定时任务已暂停，请点击「恢复执行」从头开始 — {reason}", tag="warn")
        self._start_icon_flash()

    def _create_tray_flash_icons(self, image):
        size = 32
        normal = image.copy()
        if normal.mode != "RGBA":
            normal = normal.convert("RGBA")
        normal = normal.resize((size, size), Image.Resampling.LANCZOS)

        alert = normal.copy()
        red_layer = Image.new("RGBA", alert.size, (255, 40, 40, 200))
        alert = Image.alpha_composite(alert, red_layer)

        flash = Image.new("RGBA", (size, size), (255, 30, 30, 255))
        draw_font = None
        try:
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(flash)
            try:
                draw_font = ImageFont.truetype("arial.ttf", 22)
            except OSError:
                draw_font = ImageFont.load_default()
            draw.text((size // 2, size // 2), "!", fill="white", font=draw_font, anchor="mm")
        except Exception:
            pass

        return normal, alert, flash

    def _start_icon_flash(self):
        if self._icon_flash_job is not None:
            return
        self._icon_flash_step = 0
        self._tick_icon_flash()

    def _stop_icon_flash(self):
        if self._icon_flash_job is not None:
            self.root.after_cancel(self._icon_flash_job)
            self._icon_flash_job = None
        self._icon_flash_step = 0
        self.root.title(self._window_title_normal)
        if hasattr(self, "header_emblem"):
            self.header_emblem.configure(
                text="⚡", bg=COLORS["accent_light"], fg=COLORS["accent"],
            )
        if self.tray_icon and self._tray_icon_normal:
            self.tray_icon.icon = self._tray_icon_normal
            self.tray_icon.title = self._window_title_normal

    def _tick_icon_flash(self):
        if not self.scheduler.paused:
            self._stop_icon_flash()
            return

        icons = [self._tray_icon_normal, self._tray_icon_alert, self._tray_icon_flash]
        icons = [icon for icon in icons if icon is not None]
        if self.tray_icon and icons:
            self.tray_icon.icon = icons[self._icon_flash_step % len(icons)]
            self.tray_icon.title = "⚠ MyExe — 定时任务已暂停！"

        if self._icon_flash_step % 2 == 0:
            self.root.title(f"⚠ {self._window_title_normal} — 任务已暂停")
            if hasattr(self, "header_emblem"):
                self.header_emblem.configure(
                    text="⚠", bg=COLORS["danger_light"], fg=COLORS["danger"],
                )
        else:
            self.root.title(self._window_title_normal)
            if hasattr(self, "header_emblem"):
                self.header_emblem.configure(
                    text="⚡", bg=COLORS["warning"], fg="#ffffff",
                )

        self._icon_flash_step += 1
        self._icon_flash_job = self.root.after(350, self._tick_icon_flash)

    def toggle_scheduler(self):
        if self.scheduler.running and self.scheduler.paused:
            if self.scheduler.resume():
                self._stop_icon_flash()
                self._update_scheduler_ui()
            return
        if self.scheduler.running:
            self.scheduler.stop()
            self._stop_icon_flash()
        else:
            self.scheduler.start()
        self._update_scheduler_ui()

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
        self._center_on_screen(dialog, 480, 260)

    # ── 操作录制 ──────────────────────────────────────────

    def open_macro_dialog(self):
        if self._macro_dialog and self._macro_dialog.winfo_exists():
            self._macro_dialog.lift()
            self._macro_dialog.focus_force()
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("操作录制")
        dialog.configure(bg=COLORS["bg"])
        dialog.geometry("620x540")
        dialog.resizable(True, True)
        dialog.minsize(560, 500)
        dialog.transient(self.root)
        self._macro_dialog = dialog

        frame = tk.Frame(dialog, bg=COLORS["bg"], padx=24, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            frame,
            text="配置地址 → 开始录制（自动打开浏览器）→ 保存后可一键执行或定时运行",
            bg=COLORS["bg"], fg=COLORS["text_dim"], font=_font(9),
        ).pack(anchor=tk.W, pady=(0, 14))

        form = tk.Frame(frame, bg=COLORS["bg"])
        form.pack(fill=tk.X, pady=(0, 12))

        name_row = tk.Frame(form, bg=COLORS["bg"])
        name_row.pack(fill=tk.X, pady=(0, 8))
        tk.Label(name_row, text="名称", bg=COLORS["bg"], fg=COLORS["text"],
                 font=_font(10), width=8, anchor=tk.W).pack(side=tk.LEFT)
        name_var = tk.StringVar(value="我的操作")
        name_entry = tk.Entry(
            name_row, textvariable=name_var, font=_font(10),
            bg=COLORS["surface"], fg=COLORS["text"], relief=tk.FLAT,
            highlightbackground=COLORS["border"], highlightthickness=1,
        )
        name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)

        url_row = tk.Frame(form, bg=COLORS["bg"])
        url_row.pack(fill=tk.X, pady=(0, 8))
        tk.Label(url_row, text="目标地址", bg=COLORS["bg"], fg=COLORS["text"],
                 font=_font(10), width=8, anchor=tk.W).pack(side=tk.LEFT)
        default_url = Config.get("server.clickUrl", "https://example.com")
        url_var = tk.StringVar(value=default_url)
        url_entry = tk.Entry(
            url_row, textvariable=url_var, font=_font(10),
            bg=COLORS["surface"], fg=COLORS["text"], relief=tk.FLAT,
            highlightbackground=COLORS["border"], highlightthickness=1,
        )
        url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)

        wait_row = tk.Frame(form, bg=COLORS["bg"])
        wait_row.pack(fill=tk.X, pady=(0, 8))
        tk.Label(wait_row, text="等待秒数", bg=COLORS["bg"], fg=COLORS["text"],
                 font=_font(10), width=8, anchor=tk.W).pack(side=tk.LEFT)
        wait_var = tk.StringVar(value="5")
        wait_entry = tk.Entry(
            wait_row, textvariable=wait_var, font=_font(10), width=8,
            bg=COLORS["surface"], fg=COLORS["text"], relief=tk.FLAT,
            highlightbackground=COLORS["border"], highlightthickness=1,
        )
        wait_entry.pack(side=tk.LEFT, ipady=6)
        tk.Label(wait_row, text="执行/回放前等待页面加载", bg=COLORS["bg"],
                 fg=COLORS["text_dim"], font=_font(8)).pack(side=tk.LEFT, padx=(10, 0))

        status_label = tk.Label(
            frame, text="就绪 — 按 F9 可结束录制",
            bg=COLORS["accent_light"], fg=COLORS["accent"],
            font=_font(9), padx=10, pady=6, anchor=tk.W,
        )
        status_label.pack(fill=tk.X, pady=(0, 10))

        btn_area = tk.Frame(frame, bg=COLORS["bg"])
        btn_row_main = tk.Frame(btn_area, bg=COLORS["bg"])
        btn_row_main.pack(fill=tk.X)
        btn_row_actions = tk.Frame(btn_area, bg=COLORS["bg"])
        btn_row_actions.pack(fill=tk.X, pady=(6, 0))

        record_btn = RoundedButton(btn_row_main, text="● 开始录制", variant="danger", bg=COLORS["bg"], compact=True)
        record_btn.pack(side=tk.LEFT, padx=(0, 6))
        stop_btn = RoundedButton(btn_row_main, text="■ 停止并保存", variant="success", bg=COLORS["bg"], compact=True)
        stop_btn.pack(side=tk.LEFT, padx=(0, 6))
        play_btn = RoundedButton(btn_row_main, text="▶ 执行", variant="primary", bg=COLORS["bg"], compact=True)
        play_btn.pack(side=tk.LEFT, padx=(0, 6))
        schedule_btn = RoundedButton(btn_row_main, text="⏰ 定时", variant="ghost", bg=COLORS["bg"], compact=True)
        schedule_btn.pack(side=tk.LEFT, padx=(0, 6))

        delete_btn = RoundedButton(btn_row_actions, text="删除", variant="ghost", bg=COLORS["bg"], compact=True)
        delete_btn.pack(side=tk.LEFT, padx=(0, 6))
        refresh_btn = RoundedButton(btn_row_actions, text="刷新", variant="ghost", bg=COLORS["bg"], compact=True)
        refresh_btn.pack(side=tk.LEFT, padx=(0, 6))
        close_btn = RoundedButton(
            btn_row_actions, text="关闭", command=dialog.destroy, variant="ghost", bg=COLORS["bg"], compact=True,
        )
        close_btn.pack(side=tk.RIGHT)

        btn_area.pack(side=tk.BOTTOM, fill=tk.X, pady=(8, 0))

        list_wrap = tk.Frame(
            frame, bg=COLORS["surface"],
            highlightbackground=COLORS["border"], highlightthickness=1,
        )
        list_wrap.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        columns = ("name", "url", "events", "schedule")
        tree = ttk.Treeview(list_wrap, columns=columns, show="headings", height=6)
        tree.heading("name", text="名称")
        tree.heading("url", text="地址")
        tree.heading("events", text="步骤数")
        tree.heading("schedule", text="定时")
        tree.column("name", width=100, minwidth=80)
        tree.column("url", width=220, minwidth=120)
        tree.column("events", width=60, anchor=tk.CENTER)
        tree.column("schedule", width=80, anchor=tk.CENTER)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(list_wrap, orient=tk.VERTICAL, command=tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=scroll.set)

        stop_btn.configure(state="disabled")

        def _apply_macros(macros):
            for item in tree.get_children():
                tree.delete(item)
            for macro in macros:
                macro_id = macro.get("id") or macro.get("_id")
                if not macro_id:
                    continue
                sched = macro.get("schedule") or {}
                sched_text = sched.get("time", "-") if sched.get("enabled") else "未启用"
                tree.insert("", tk.END, iid=macro_id, values=(
                    macro.get("name", ""),
                    macro.get("url", "")[:40],
                    len(macro.get("events", [])),
                    sched_text,
                ))
            if not self._recording:
                status_label.configure(
                    text="就绪 — 按 F9 可结束录制",
                    bg=COLORS["accent_light"], fg=COLORS["accent"],
                )

        def _refresh_list(show_loading=True):
            if show_loading and not self._recording:
                status_label.configure(
                    text="正在从服务端加载列表...",
                    bg=COLORS["warning"], fg="#ffffff",
                )

            def _load():
                try:
                    macros = list_macros()
                except MacroApiError as e:
                    self.root.after(0, lambda: (
                        self.print_to_gui(f"[Macro] 加载失败: {e}", tag="error"),
                        status_label.configure(
                            text="加载失败，请点击「刷新」重试",
                            bg=COLORS["danger_light"], fg=COLORS["danger"],
                        ) if not self._recording else None,
                    ))
                    return
                self.root.after(0, lambda: _apply_macros(macros))

            threading.Thread(target=_load, daemon=True).start()

        def _parse_url():
            url = url_var.get().strip()
            if not url.startswith(("http://", "https://")):
                self.print_to_gui("地址需以 http:// 或 https:// 开头", tag="warn")
                return None
            return url

        def _parse_wait():
            try:
                w = int(wait_var.get().strip())
                return max(1, min(w, 120))
            except ValueError:
                return 5

        def _set_recording_ui(recording):
            self._recording = recording
            if recording:
                status_label.configure(
                    text="● 录制中 — 在浏览器中操作，完成后按 F9 或点击「停止并保存」",
                    bg=COLORS["danger_light"], fg=COLORS["danger"],
                )
                record_btn.configure(state="disabled")
                stop_btn.configure(state="normal")
                name_entry.configure(state="disabled")
                url_entry.configure(state="disabled")
                wait_entry.configure(state="disabled")
            else:
                status_label.configure(
                    text="就绪 — 按 F9 可结束录制",
                    bg=COLORS["accent_light"], fg=COLORS["accent"],
                )
                record_btn.configure(state="normal")
                stop_btn.configure(state="disabled")
                name_entry.configure(state="normal")
                url_entry.configure(state="normal")
                wait_entry.configure(state="normal")

        def _start_record():
            url = _parse_url()
            if url is None:
                return
            name = name_var.get().strip() or "未命名操作"
            wait_sec = _parse_wait()

            def _do_record():
                open_browser(url, self.print_to_gui)
                self.root.after(0, lambda: status_label.configure(
                    text=f"浏览器已打开，{wait_sec}s 后开始录制...",
                    bg=COLORS["warning"], fg="#ffffff",
                ))
                time.sleep(wait_sec)
                try:
                    self.macro_recorder.start()
                except RuntimeError as e:
                    self.root.after(0, lambda: self.print_to_gui(str(e), tag="error"))
                    return
                self.root.after(0, _set_recording_ui, True)
                events = self.macro_recorder.wait_until_stopped()
                macro = {
                    "_id": str(uuid.uuid4()),
                    "name": name,
                    "url": url,
                    "wait_seconds": wait_sec,
                    "events": events,
                }
                try:
                    save_macro(macro)
                except MacroApiError as e:
                    self.root.after(0, lambda: (
                        _set_recording_ui(False),
                        self.print_to_gui(f"[Macro] 保存失败: {e}", tag="error"),
                    ))
                    return
                self.root.after(0, lambda: (
                    _set_recording_ui(False),
                    _refresh_list(show_loading=False),
                    self.print_to_gui(f"[Macro] 已保存「{name}」，共 {len(events)} 步", tag="success"),
                ))

            threading.Thread(target=_do_record, daemon=True).start()

        def _stop_record():
            if self.macro_recorder.recording:
                self.macro_recorder.stop()

        def _get_selected_id():
            sel = tree.selection()
            if not sel:
                self.print_to_gui("请先在列表中选择一条录制", tag="warn")
                return None
            return sel[0]

        def _play_selected():
            macro_id = _get_selected_id()
            if not macro_id:
                return
            macro = load_macro(macro_id)
            if not macro:
                self.print_to_gui("录制文件不存在", tag="warn")
                return
            play_btn.configure(state="disabled")

            def _run():
                self.macro_player.play(macro)
                self.root.after(0, lambda: play_btn.configure(state="normal"))

            threading.Thread(target=_run, daemon=True).start()

        def _delete_selected():
            macro_id = _get_selected_id()
            if not macro_id:
                return
            macro = load_macro(macro_id)
            name = macro.get("name", macro_id) if macro else macro_id

            def _do_delete():
                try:
                    delete_macro(macro_id)
                except MacroApiError as e:
                    self.root.after(0, lambda: self.print_to_gui(f"[Macro] 删除失败: {e}", tag="error"))
                    return
                self.root.after(0, lambda: (
                    _refresh_list(show_loading=False),
                    self.print_to_gui(f"[Macro] 已删除「{name}」", tag="success"),
                ))

            threading.Thread(target=_do_delete, daemon=True).start()

        def _open_schedule():
            macro_id = _get_selected_id()
            if not macro_id:
                return
            macro = load_macro(macro_id)
            if not macro:
                return

            sched_dialog = tk.Toplevel(dialog)
            sched_dialog.title("定时执行")
            sched_dialog.configure(bg=COLORS["bg"])
            sched_dialog.geometry("360x200")
            sched_dialog.resizable(False, False)
            sched_dialog.transient(dialog)
            sched_dialog.grab_set()

            sf = tk.Frame(sched_dialog, bg=COLORS["bg"], padx=24, pady=20)
            sf.pack(fill=tk.BOTH, expand=True)

            schedule = macro.get("schedule") or {}
            enabled_var = tk.BooleanVar(value=bool(schedule.get("enabled")))
            time_var = tk.StringVar(value=schedule.get("time", "09:00"))

            tk.Checkbutton(
                sf, text="启用每日定时执行", variable=enabled_var,
                bg=COLORS["bg"], fg=COLORS["text"], font=_font(10),
                activebackground=COLORS["bg"], selectcolor=COLORS["surface"],
            ).pack(anchor=tk.W, pady=(0, 12))

            tr = tk.Frame(sf, bg=COLORS["bg"])
            tr.pack(fill=tk.X, pady=(0, 16))
            tk.Label(tr, text="执行时间", bg=COLORS["bg"], fg=COLORS["text"],
                     font=_font(10), width=8, anchor=tk.W).pack(side=tk.LEFT)
            tk.Entry(
                tr, textvariable=time_var, font=_font(10), width=10,
                bg=COLORS["surface"], fg=COLORS["text"], relief=tk.FLAT,
                highlightbackground=COLORS["border"], highlightthickness=1,
            ).pack(side=tk.LEFT, ipady=6)
            tk.Label(tr, text="格式 HH:MM，如 09:30", bg=COLORS["bg"],
                     fg=COLORS["text_dim"], font=_font(8)).pack(side=tk.LEFT, padx=(8, 0))

            br = tk.Frame(sf, bg=COLORS["bg"])
            br.pack(fill=tk.X)

            def _save_schedule():
                t = time_var.get().strip()
                if enabled_var.get():
                    parts = t.split(":")
                    if len(parts) != 2:
                        self.print_to_gui("时间格式应为 HH:MM", tag="warn")
                        return
                    try:
                        h, m = int(parts[0]), int(parts[1])
                        if not (0 <= h <= 23 and 0 <= m <= 59):
                            raise ValueError
                    except ValueError:
                        self.print_to_gui("时间无效，请使用 00:00 - 23:59", tag="warn")
                        return
                macro["schedule"] = {
                    "enabled": enabled_var.get(),
                    "time": t,
                    "last_run": schedule.get("last_run", ""),
                }

                def _do_save():
                    try:
                        save_macro(macro)
                    except MacroApiError as e:
                        self.root.after(0, lambda: self.print_to_gui(f"[Macro] 定时保存失败: {e}", tag="error"))
                        return
                    self.root.after(0, lambda: (
                        _refresh_list(show_loading=False),
                        self.print_to_gui(
                            f"[Macro] 「{macro.get('name')}」定时已{'启用' if enabled_var.get() else '关闭'}",
                            tag="success",
                        ),
                        sched_dialog.destroy(),
                    ))

                threading.Thread(target=_do_save, daemon=True).start()

            RoundedButton(br, text="保存", command=_save_schedule, variant="success", bg=COLORS["bg"]).pack(side=tk.LEFT)
            RoundedButton(br, text="取消", command=sched_dialog.destroy, variant="ghost", bg=COLORS["bg"]).pack(side=tk.RIGHT)
            self._center_on_screen(sched_dialog, 360, 200)

        record_btn.configure(command=_start_record)
        stop_btn.configure(command=_stop_record)
        play_btn.configure(command=_play_selected)
        schedule_btn.configure(command=_open_schedule)
        delete_btn.configure(command=_delete_selected)
        refresh_btn.configure(command=_refresh_list)

        def _on_tree_select(_event=None):
            sel = tree.selection()
            if not sel:
                return
            macro = load_macro(sel[0])
            if macro:
                name_var.set(macro.get("name", ""))
                url_var.set(macro.get("url", ""))
                wait_var.set(str(macro.get("wait_seconds", 5)))

        tree.bind("<<TreeviewSelect>>", _on_tree_select)

        _refresh_list()
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        self._center_on_screen(dialog, 620, 540)

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
            self._tray_icon_normal, self._tray_icon_alert, self._tray_icon_flash = (
                self._create_tray_flash_icons(image)
            )
            self.tray_icon = pystray.Icon("MyExe", self._tray_icon_normal, self._window_title_normal, menu)
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

    def _center_on_screen(self, window, width=None, height=None):
        window.update_idletasks()
        w = width or window.winfo_width()
        h = height or window.winfo_height()
        x = max(0, (window.winfo_screenwidth() - w) // 2)
        y = max(0, (window.winfo_screenheight() - h) // 2)
        window.geometry(f"{w}x{h}+{x}+{y}")

    def _center_window(self, width=None, height=None):
        self._center_on_screen(self.root, width, height)

    def _show_window(self):
        self.is_minimized = False
        self._center_window()
        self.root.deiconify()
        self.root.state("normal")
        self.root.lift()
        self.root.focus_force()

    def _on_root_unmap(self, event):
        if event.widget != self.root or self.is_minimized:
            return
        if self.root.state() == "iconic":
            self.root.after(0, self.minimize_to_tray)

    def minimize_to_tray(self):
        if self.is_minimized:
            return
        self.is_minimized = True
        self.root.withdraw()
        self.print_to_gui("程序已最小化到系统托盘")

    def toggle_server_from_tray(self, icon=None, item=None):
        self.root.after(0, self.toggle_server)

    def toggle_scheduler_from_tray(self, icon=None, item=None):
        self.root.after(0, self.toggle_scheduler)

    def on_closing(self):
        self._quit_app()

    def quit_app(self, icon=None, item=None):
        self.root.after(0, self._quit_app)

    def _quit_app(self):
        if self.tray_icon:
            self.tray_icon.stop()
        self.exit_app()

    def exit_app(self):
        self._stop_icon_flash()
        if self.server.running:
            self.server.stop()
        if self.proxy.running:
            self.proxy.stop()
        if self.scheduler.running:
            self.scheduler.stop()
        if self.macro_scheduler.running:
            self.macro_scheduler.stop()
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()


def run():
    root = tk.Tk()
    root.withdraw()
    MyApp(root)
    root.deiconify()
    root.mainloop()
