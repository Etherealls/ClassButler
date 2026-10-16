const { app, BrowserWindow, ipcMain } = require('electron')
const { spawn } = require('child_process')
const path = require('path')
const fs = require('fs')

let backendProcess = null
let mainWindow = null

// 后端可执行文件路径：打包后位于 resources/backend/backend.exe
function getBackendPath() {
  const candidates = [
    path.join(process.resourcesPath, 'backend', 'backend.exe'),
    path.join(__dirname, '..', 'backend', 'backend.exe'),
    path.join(__dirname, 'backend.exe'),
  ]
  for (const c of candidates) {
    if (fs.existsSync(c)) return c
  }
  return null
}

// 前端静态文件：开发时用 Vite dev server，打包后加载 FastAPI 托管的页面
function getFrontendUrl() {
  if (process.env.VITE_DEV_SERVER_URL) {
    return process.env.VITE_DEV_SERVER_URL
  }
  return null
}

function startBackend() {
  const backendPath = getBackendPath()
  if (!backendPath) {
    console.error('未找到 backend.exe，将以开发模式运行（需单独启动后端）')
    return
  }
  backendProcess = spawn(backendPath, [], {
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
  })

  backendProcess.stdout.on('data', (chunk) => {
    const text = chunk.toString()
    // 后端启动后输出 PORT=<port>
    const match = text.match(/PORT=(\d+)/)
    if (match && mainWindow) {
      mainWindow.loadURL(`http://127.0.0.1:${match[1]}/`)
    }
  })

  backendProcess.stderr.on('data', (chunk) => {
    console.log('[backend]', chunk.toString())
  })

  backendProcess.on('exit', (code) => {
    console.log('backend exited with code', code)
  })
}

function stopBackend() {
  if (backendProcess) {
    backendProcess.kill()
    backendProcess = null
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 1024,
    minHeight: 700,
    title: '班主任学生管理系统',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  const devUrl = getFrontendUrl()
  if (devUrl) {
    mainWindow.loadURL(devUrl)
  }
  // 否则等待后端启动输出端口后再加载（在 startBackend 中处理）

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

app.whenReady().then(() => {
  startBackend()
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  stopBackend()
  if (process.platform !== 'darwin') app.quit()
})

app.on('before-quit', () => {
  stopBackend()
})
