/**
 * AI 读书会桌面端（Electron）
 *
 * 启动逻辑：
 * 1. 若设置了 AIREADER_SERVER，直接连接该服务；
 * 2. 否则尝试在本机拉起后端：python3 -m uvicorn app.main:app（需要后端依赖）；
 * 3. 等 /api/health 就绪后打开窗口。
 *
 * 前端构建产物由后端在生产模式下统一托管（frontend/dist）。
 */
const { app, BrowserWindow, shell, Menu } = require('electron')
const { spawn } = require('child_process')
const path = require('path')
const http = require('http')

// Linux root 容器环境需要关闭沙箱；普通用户桌面无需此设置
if (process.getuid && process.getuid() === 0) {
  app.commandLine.appendSwitch('no-sandbox')
}

const PORT = process.env.AIREADER_PORT || 8000
const SERVER = process.env.AIREADER_SERVER || `http://127.0.0.1:${PORT}`
let backend = null

function waitHealth(url, timeoutMs = 60000) {
  return new Promise((resolve, reject) => {
    const start = Date.now()
    const tick = () => {
      http.get(`${url}/api/health`, (res) => {
        if (res.statusCode === 200) { res.resume(); resolve(); return }
        res.resume(); retry()
      }).on('error', retry)
    }
    const retry = () => {
      if (Date.now() - start > timeoutMs) return reject(new Error('backend timeout'))
      setTimeout(tick, 700)
    }
    tick()
  })
}

function startBackend() {
  if (process.env.AIREADER_SERVER) return null
  const backendDir = path.resolve(__dirname, '..', 'backend')
  const python = process.platform === 'win32' ? 'python' : 'python3'
  const child = spawn(python, ['-m', 'uvicorn', 'app.main:app', '--port', String(PORT)], {
    cwd: backendDir,
    env: process.env,
    stdio: 'ignore',
  })
  child.on('error', () => { /* 无 Python 时停在连接页 */ })
  return child
}

async function createWindow() {
  backend = startBackend()
  const win = new BrowserWindow({
    width: 1380,
    height: 900,
    minWidth: 900,
    minHeight: 600,
    title: 'AI 读书会 · 陪读阅读器',
    backgroundColor: '#f5efe3',
    webPreferences: { contextIsolation: true, nodeIntegration: false },
  })
  Menu.setApplicationMenu(null)
  win.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: 'deny' } })

  win.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(
    '<body style="font-family:sans-serif;background:#f5efe3;color:#57504a;display:grid;place-items:center;height:100vh;margin:0">' +
    '<div style="text-align:center"><h2>AI 读书会正在启动…</h2><p>首次启动会初始化 AI 分析引擎，请稍候</p></div></body>'))

  try {
    await waitHealth(SERVER)
    win.loadURL(SERVER)
  } catch {
    win.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(
      '<body style="font-family:sans-serif;background:#f5efe3;color:#57504a;display:grid;place-items:center;height:100vh;margin:0">' +
      `<div style="text-align:center;max-width:420px"><h2>未能连接后端</h2><p>请先启动后端服务：<br><code>cd backend && uvicorn app.main:app --port ${PORT}</code></p><p>或设置 AIREADER_SERVER 环境变量后重启。</p></div></body>`))
  }
}

app.whenReady().then(createWindow)
app.on('window-all-closed', () => {
  if (backend) try { backend.kill() } catch {}
  if (process.platform !== 'darwin') app.quit()
})
