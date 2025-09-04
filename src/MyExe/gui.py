import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from MyExe.server import FastAPIServer
from MyExe.scheduler import SimpleScheduler
from MyExe.utils.time_utils import current_datetime_str, current_date_str, current_time_str
from MyExe.utils.config_loader import Config

class MyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MyExe 控制台")
        self.root.geometry("600x400")

        # 日志输出框
        self.log_text = ScrolledText(root, state='disabled', height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5)

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

        self.exit_btn = tk.Button(frame, text="退出", width=10, command=self.exit_app)
        self.exit_btn.pack(side=tk.LEFT, padx=5)

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

    def exit_app(self):
        if self.server.running:
            self.server.stop()
        if self.scheduler.running:
            self.scheduler.stop()
        self.root.quit()


def run():
    root = tk.Tk()
    app = MyApp(root)
    root.mainloop()
