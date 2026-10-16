# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 打包配置：把 FastAPI 后端打包为 backend.exe
# 使用方式：pyinstaller build_backend.spec

import sys
from pathlib import Path

block_cipher = None

# 收集前端静态文件（若已构建）
frontend_dist = Path(__file__).resolve().parent.parent / 'frontend' / 'dist'
datas = []
if (frontend_dist / 'index.html').exists():
    datas.append((str(frontend_dist), '_static'))

a = Analysis(
    ['main.py'],
    pathex=[str(Path(__file__).resolve().parent)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops.auto',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan.on',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'pytest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
