const { contextBridge } = require('electron')

// 预留安全桥接能力（当前前端直接通过 HTTP 与本地后端通信，无需额外暴露）
contextBridge.exposeInMainWorld('classManager', {
  platform: process.platform,
})
