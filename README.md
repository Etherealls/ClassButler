# 班主任学生管理系统

一个面向高职班主任的 **Windows 单机桌面软件**，覆盖学生档案、考勤请假、查寝、纪律、成绩统计、学业预警、数据看板等高频刚需，做到"录入一次、全程复用、自动出表"。

## 特性

- **单机零配置**：内置 Python 运行时与 SQLite 数据库，目标电脑无需安装任何环境，双击即用，全程离线。
- **单角色**：仅班主任一人登录使用（默认 `admin` / `admin123`，首次登录强制改密）。
- **四大模块**：
  - M1 基础档案与组织（学生档案、家长、干部、宿舍、座位、值日、花名册导入导出）
  - M2 日常行为管理（考勤、请假、查寝、纪律）
  - M3 学业与成绩（成绩排名统计、学业预警、补考重修、竞赛证书）
  - M4 数据看板与系统底座（看板、全局搜索、审计日志、自动备份）
- **安全**：密码 bcrypt 加盐、JWT 本地签发、仅监听 `127.0.0.1`、敏感字段脱敏、软删除留痕。

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + Vite + TypeScript + Element Plus + Pinia + Vue Router + ECharts |
| 后端 | FastAPI + SQLAlchemy 2.0 + Pydantic v2 + python-jose(JWT) + passlib(bcrypt) |
| 数据库 | SQLite（嵌入式，单文件，随软件走） |
| 桌面壳 | Electron + PyInstaller（可选 Inno Setup） |

## 目录结构

```
class-manager/
├── backend/                # FastAPI 后端
│   ├── app/
│   │   ├── api/            # 各模块路由
│   │   ├── core/           # 配置、数据库、安全、依赖
│   │   ├── models/         # SQLAlchemy 模型
│   │   ├── schemas/        # Pydantic 模型
│   │   ├── services/       # 初始化服务
│   │   └── utils/          # 工具（导入导出/脱敏/备份）
│   ├── main.py             # 入口
│   ├── build_backend.spec  # PyInstaller 配置
│   └── requirements.txt
├── frontend/               # Vue3 前端
│   ├── src/
│   │   ├── api/            # Axios 封装
│   │   ├── layout/         # 主布局
│   │   ├── router/         # 路由
│   │   ├── store/          # Pinia
│   │   └── views/          # 页面
│   └── vite.config.ts
├── electron/               # Electron 桌面壳
│   ├── main.js
│   └── preload.js
├── installer/              # Inno Setup 脚本
└── 班主任学生管理系统-开发文档.md
```

## 本地开发

### 后端

```bash
cd backend
pip install -r requirements.txt
python main.py 8000        # 指定端口启动；省略则自动随机端口
```

后端默认监听 `127.0.0.1`，数据存于 `%APPDATA%/ClassManager/`。接口文档：`http://127.0.0.1:8000/api/docs`。

### 前端

```bash
cd frontend
npm install
npm run dev                # Vite dev server，代理 /api 到 127.0.0.1:8000
```

### 构建

```bash
# 1. 构建前端静态产物
cd frontend && npm run build

# 2. 打包后端为 backend.exe（需安装 PyInstaller）
cd backend && pyinstaller build_backend.spec

# 3. 打包桌面安装包（需安装 Electron）
cd electron && npm install && npm run dist
```

## 打包说明（零配置分发）

1. **后端**：PyInstaller 将 FastAPI + 依赖 + 前端静态文件打包为单个 `backend.exe`（内含 Python 运行时）。
2. **前端**：`vite build` 产物由后端静态托管。
3. **桌面壳**：Electron 主进程拉起 `backend.exe`（监听随机空闲端口），窗口关闭时终止后端。
4. **安装包**：Electron Builder 的 NSIS 或 Inno Setup 生成 `_setup.exe`，双击安装。

数据目录与程序目录分离：数据库、备份、附件均存于 `%APPDATA%/ClassManager/`，卸载或升级不影响数据。

## 数据备份

- 软件启动/退出时自动备份 SQLite 到备份目录，保留最近 14 份。
- 系统内"账号设置"页提供"立即备份"与备份记录查看。
- 换机迁移：拷贝 `%APPDATA%/ClassManager/` 整个目录即可。

## 默认账号

- 账号：`admin`
- 密码：`admin123`
- 首次登录强制修改密码。

## 许可

本项目为内部使用系统，仅供班主任本人单机使用。
