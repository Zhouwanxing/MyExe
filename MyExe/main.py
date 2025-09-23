import sys
import os
import logging
from pathlib import Path

# 添加当前目录到 Python 路径，确保可以找到同级模块
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# 尝试不同的导入方式
try:
    from gui import run
except ImportError:
    # 如果直接导入失败，尝试从 MyExe 包导入
    from MyExe.gui import run

sys.stdout = open("stdout.log", "w", buffering=1)
sys.stderr = open("stderr.log", "w", buffering=1)
logging.basicConfig(filename="app.log", level=logging.DEBUG)

if __name__ == "__main__":
    run()
