"""FastAPI 主入口"""
import sys
import uuid
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import (
    attendance,
    auth,
    dashboard,
    discipline,
    dorm_check,
    honors,
    leaves,
    organization,
    scores,
    students,
    system,
)
from app.core.config import settings
from app.core.deps import get_current_user
from app.core.response import BizError, ok, register_exception_handlers
from app.services import init_database

app = FastAPI(title="班主任学生管理系统", version="1.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json")

# 仅本机访问，CORS 放宽到 localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

API_PREFIX = "/api/v1"

# 注册路由
for module in [
    auth, students, organization, attendance, leaves, dorm_check,
    discipline, scores, honors, dashboard, system,
]:
    app.include_router(module.router, prefix=API_PREFIX)


@app.get("/api/v1/health")
def health():
    return ok({"status": "ok"})


@app.post("/api/v1/upload")
async def upload_file(file: UploadFile = File(...), _=Depends(get_current_user)):
    """通用文件上传（证件照、请假附件、证书扫描件），限 JPG/PNG，≤2MB"""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png"):
        raise BizError("仅支持 JPG/PNG 格式", 400)
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise BizError("文件大小不能超过 2MB", 400)
    fname = f"{uuid.uuid4().hex}{ext}"
    dest = settings.upload_dir / fname
    dest.write_bytes(content)
    return ok({"url": f"/uploads/{fname}"})


# 静态文件：上传附件 + 前端产物
app.mount("/uploads", StaticFiles(directory=str(settings.upload_dir)), name="uploads")


@app.on_event("startup")
def on_startup():
    init_database()


def _serve_spa():
    """挂载前端 SPA（若静态目录存在）"""
    static_dir = settings.static_dir
    if (static_dir / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="spa")


def run_server(host: str = "127.0.0.1", port: int = 0):
    """由 Electron/PyInstaller 调用：绑定端口并输出端口号到 stdout"""
    _serve_spa()
    import socket

    # 预绑定一个空闲端口，拿到端口号后释放，交给 uvicorn 使用
    # （本机单机场景端口冲突概率极低）
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, port))
    actual_port = sock.getsockname()[1]
    sock.close()

    print(f"PORT={actual_port}", flush=True)
    uvicorn.run(app, host=host, port=actual_port, log_level="info")


if __name__ == "__main__":
    _serve_spa()
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    if port == 0:
        run_server()
    else:
        uvicorn.run(app, host="127.0.0.1", port=port)
