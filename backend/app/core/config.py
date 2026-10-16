"""班主任学生管理系统 - 后端配置模块"""
import os
import sys
from pathlib import Path


def get_appdata_dir() -> Path:
    """返回数据目录：Windows %APPDATA%/ClassManager，其他平台 ~/.classmanager"""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", str(Path.home()))
    else:
        base = str(Path.home() / ".classmanager")
    data_dir = Path(base) / "ClassManager"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


class Settings:
    """全局配置。单机版：数据库、备份、附件均存于数据目录，与程序分离。"""

    def __init__(self):
        self.data_dir = get_appdata_dir()
        self.backup_dir = self.data_dir / "backups"
        self.upload_dir = self.data_dir / "uploads"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.data_dir / "class_manager.db"
        self.database_url = f"sqlite:///{self.db_path.as_posix()}"

        # JWT 密钥：优先读取环境变量，否则按数据目录生成持久化密钥
        env_secret = os.environ.get("CLASSMANAGER_SECRET")
        if env_secret:
            self.secret_key = env_secret
        else:
            secret_file = self.data_dir / ".secret"
            if secret_file.exists():
                self.secret_key = secret_file.read_text(encoding="utf-8").strip()
            else:
                self.secret_key = os.urandom(32).hex()
                secret_file.write_text(self.secret_key, encoding="utf-8")

        self.algorithm = "HS256"
        self.access_token_expire_minutes = 120  # 2 小时
        self.refresh_token_expire_days = 7
        self.backup_keep_count = 14
        self.default_username = "admin"
        self.default_password = "admin123"

    @property
    def static_dir(self) -> Path:
        """前端静态文件目录（打包后由 backend.exe 托管）"""
        # 开发时：backend/../frontend/dist；打包后：可执行文件旁 _static
        candidates = [
            Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "dist",
            Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "_static",
        ]
        for c in candidates:
            if (c / "index.html").exists():
                return c
        return candidates[0]


settings = Settings()
