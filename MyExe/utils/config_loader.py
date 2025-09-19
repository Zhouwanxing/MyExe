import yaml
import os
from pathlib import Path

class Config:
    _cfg = None

    @classmethod
    def load(cls):
        if cls._cfg is None:
            # # 获取项目根目录
            # # base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            # # 当前文件目录
            # current_dir = os.path.dirname(os.path.abspath(__file__))
            #
            # # src 目录
            # src_dir = os.path.dirname(current_dir)
            #
            # # 项目根目录（最外层）
            # base_dir = os.path.dirname(src_dir)
            # print(base_dir)
            current_file = Path(__file__).resolve()
            project_root = current_file

            # 向上查找，直到找到 .env 或 config 文件夹
            while not (project_root / "config").exists():
                project_root = project_root.parent
            print(project_root)

            cfg_path = os.path.join(project_root, "config", "config.yaml")
            with open(cfg_path, "r", encoding="utf-8") as f:
                cls._cfg = yaml.safe_load(f)
        return cls._cfg

    @classmethod
    def get(cls, key_path, default=None):
        """
        支持点分路径获取配置，例如 "server.host"
        """
        cfg = cls.load()
        keys = key_path.split(".")
        for k in keys:
            if isinstance(cfg, dict) and k in cfg:
                cfg = cfg[k]
            else:
                return default
        return cfg
