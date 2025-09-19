import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import pystray
from PIL import Image
import threading
import sys
import os

# 尝试不同的导入方式以兼容 PyInstaller 打包
try:
    from server import FastAPIServer
    from scheduler import SimpleScheduler
    from utils.time_utils import current_datetime_str
    from utils.config_loader import Config
except ImportError:
    # 如果直接导入失败，尝试从 MyExe 包导入
    from MyExe.server import FastAPIServer
    from MyExe.scheduler import SimpleScheduler
    from MyExe.utils.time_utils import current_datetime_str
    from MyExe.utils.config_loader import Config

class MyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MyExe 控制台")
        self.root.geometry("600x400")
        
        # 系统托盘相关
        self.tray_icon = None
        self.tray_thread = None
        self.is_minimized = False

        # 日志输出框
        self.log_text = ScrolledText(root, state='disabled', height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5)

        # 资源路径解析（兼容 PyInstaller 打包与源码运行）
        # 定义为实例方法，供全类调用
        def _resource_path(relative_path):
            # 冻结后：
            # - 单文件模式(onefile)：存在 sys._MEIPASS
            # - 单目录模式(onedir)：sys.frozen 为 True，资源位于可执行文件同目录
            if hasattr(sys, '_MEIPASS'):
                base_path = sys._MEIPASS  # type: ignore[attr-defined]
            elif getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            return os.path.join(base_path, relative_path)

        # 绑定为实例属性，供其它方法使用
        self._resource_path = _resource_path

        # 设置窗口图标（在 log_text 创建之后）
        try:
            # 尝试多个可能的图标路径，优先使用 ICO 格式
            icon_paths = [
                self._resource_path('jerry.ico'),
                self._resource_path('icon.ico'),
                self._resource_path('jerry.png'),
                self._resource_path('icon.png')
            ]
            
            icon_set = False
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    # 检查文件扩展名
                    if icon_path.lower().endswith('.ico'):
                        # ICO 文件直接使用
                        self.root.iconbitmap(icon_path)
                        icon_set = True
                        break
                    elif icon_path.lower().endswith('.png'):
                        # PNG 文件需要转换为 PhotoImage
                        try:
                            from PIL import Image, ImageTk
                            img = Image.open(icon_path)
                            # 调整大小为 32x32
                            img = img.resize((32, 32), Image.Resampling.LANCZOS)
                            photo = ImageTk.PhotoImage(img)
                            self.root.iconphoto(False, photo)
                            # 保存引用防止被垃圾回收
                            self.icon_photo = photo
                            icon_set = True
                            break
                        except Exception as e:
                            self.print_to_gui(f"PNG 图标转换失败 {icon_path}: {e}")
                            continue
            
            if not icon_set:
                self.print_to_gui("警告: 未找到可用的图标文件，使用默认图标")
        except Exception as e:
            self.print_to_gui(f"设置窗口图标失败: {e}")

        # 服务与任务
        self.server = FastAPIServer(port=Config.get("server.port"), gui_logger=self.print_to_gui)
        self.scheduler = SimpleScheduler(interval=5, gui_logger=self.print_to_gui)

        # 按钮
        frame = tk.Frame(root)
        frame.pack(pady=5)

        self.server_btn = tk.Button(frame, text="启动 HTTP 服务", width=15, command=self.toggle_server)
        self.server_btn.pack(side=tk.LEFT, padx=5)

        self.scheduler_btn = tk.Button(frame, text="启动定时任务", width=15, command=self.toggle_scheduler)
        self.scheduler_btn.pack(side=tk.LEFT, padx=5)

        self.minimize_btn = tk.Button(frame, text="最小化到托盘", width=15, command=self.minimize_to_tray)
        self.minimize_btn.pack(side=tk.LEFT, padx=5)

        self.exit_btn = tk.Button(frame, text="退出", width=10, command=self.exit_app)
        self.exit_btn.pack(side=tk.LEFT, padx=5)
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 启动系统托盘
        self.setup_system_tray()

    def print_to_gui(self, msg):
        """将日志打印到 GUI"""
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, "[" + current_datetime_str() + "]:" + msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')

    def toggle_server(self):
        if self.server.running:
            self.server.stop()
            self.server_btn.config(text="启动 HTTP 服务")
        else:
            self.server.start()
            self.server_btn.config(text="暂停 HTTP 服务")

    def toggle_scheduler(self):
        if self.scheduler.running:
            self.scheduler.stop()
            self.scheduler_btn.config(text="启动定时任务")
        else:
            self.scheduler.start()
            self.scheduler_btn.config(text="暂停定时任务")

    def setup_system_tray(self):
        """设置系统托盘"""
        try:
            # 创建托盘图标
            icon_paths = [
                self._resource_path('jerry.png'),
                self._resource_path('jerry.ico'),
                self._resource_path('icon.ico'),
                self._resource_path('icon.png')
            ]
            
            image = None
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    try:
                        image = Image.open(icon_path)
                        # 托盘图标在 Windows 上以 16/24/32 常见，这里固定 32x32 且使用 RGBA
                        if image.mode != 'RGBA':
                            image = image.convert('RGBA')
                        image = image.resize((32, 32), Image.Resampling.LANCZOS)
                        break
                    except Exception as e:
                        self.print_to_gui(f"加载图标失败 {icon_path}: {e}")
                        continue
            
            if image is None:
                # 创建一个简单的图标
                image = Image.new('RGB', (64, 64), color='blue')
                self.print_to_gui("使用默认蓝色图标作为系统托盘图标")
            
            # 创建右键菜单
            menu = pystray.Menu(
                pystray.MenuItem("显示窗口", self.show_window),
                pystray.MenuItem("启动 HTTP 服务", self.toggle_server_from_tray),
                pystray.MenuItem("启动定时任务", self.toggle_scheduler_from_tray),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出", self.quit_app)
            )
            
            # 保存引用，避免被 GC
            self.tray_image = image
            self.tray_icon = pystray.Icon("MyExe", self.tray_image, "MyExe 控制台", menu)
            
            # 在单独线程中运行托盘
            self.tray_thread = threading.Thread(target=self.run_tray, daemon=True)
            self.tray_thread.start()
            
        except Exception as e:
            self.print_to_gui(f"系统托盘设置失败: {e}")
    
    def run_tray(self):
        """运行系统托盘"""
        try:
            self.tray_icon.run()
        except Exception as e:
            self.print_to_gui(f"系统托盘运行错误: {e}")
    
    def show_window(self, icon=None, item=None):
        """显示主窗口"""
        self.root.after(0, self._show_window)
    
    def _show_window(self):
        """在主线程中显示窗口"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.is_minimized = False
    
    def minimize_to_tray(self):
        """最小化到系统托盘"""
        self.root.withdraw()
        self.is_minimized = True
        self.print_to_gui("程序已最小化到系统托盘")
    
    def toggle_server_from_tray(self, icon=None, item=None):
        """从托盘切换服务器状态"""
        self.root.after(0, self.toggle_server)
    
    def toggle_scheduler_from_tray(self, icon=None, item=None):
        """从托盘切换调度器状态"""
        self.root.after(0, self.toggle_scheduler)
    
    def on_closing(self):
        """窗口关闭事件处理"""
        if self.is_minimized:
            # 如果已经最小化到托盘，则隐藏窗口
            self.root.withdraw()
        else:
            # 否则最小化到托盘
            self.minimize_to_tray()
    
    def quit_app(self, icon=None, item=None):
        """退出应用程序"""
        self.root.after(0, self._quit_app)
    
    def _quit_app(self):
        """在主线程中退出应用"""
        if self.tray_icon:
            self.tray_icon.stop()
        self.exit_app()
    
    def exit_app(self):
        if self.server.running:
            self.server.stop()
        if self.scheduler.running:
            self.scheduler.stop()
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()


def run():
    root = tk.Tk()
    app = MyApp(root)
    root.mainloop()
