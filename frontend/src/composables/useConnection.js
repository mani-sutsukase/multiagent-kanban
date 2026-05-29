import { ref } from 'vue'

const HEALTH_URL = '/api/health'
const HEALTH_INTERVAL = 10000  // 正常心跳间隔 10s
const RETRY_INTERVAL = 2000    // 重启后重试间隔 2s

// 全局单例状态，所有组件共享
const apiConnected = ref(true)
const serverRestarting = ref(false)
let healthTimer = null

async function checkHealth() {
  try {
    const res = await fetch(HEALTH_URL, { method: 'GET' })
    return res.ok
  } catch {
    return false
  }
}

function startHealthPing() {
  stopHealthPing()
  healthTimer = setInterval(async () => {
    apiConnected.value = await checkHealth()
  }, HEALTH_INTERVAL)
}

function stopHealthPing() {
  if (healthTimer) {
    clearInterval(healthTimer)
    healthTimer = null
  }
}

async function restartServer() {
  serverRestarting.value = true
  apiConnected.value = false
  stopHealthPing()

  // 先通知后端退出进程
  try {
    await fetch('/api/restart', { method: 'POST' })
  } catch {
    // 服务器可能立即断开，忽略 fetch 错误
  }

  // 等待一小段时间让服务器完全关闭
  await new Promise((r) => setTimeout(r, 1500))

  // 轮询等待服务器重新上线
  while (true) {
    const ok = await checkHealth()
    if (ok) {
      serverRestarting.value = false
      // 服务器已恢复，刷新整个客户端
      window.location.reload()
      return
    }
    await new Promise((r) => setTimeout(r, RETRY_INTERVAL))
  }
}

// 立即执行一次健康检查，初始化连接状态
checkHealth().then((ok) => {
  apiConnected.value = ok
})

export function useConnection() {
  return {
    apiConnected,
    serverRestarting,
    startHealthPing,
    stopHealthPing,
    restartServer,
    checkHealth,
  }
}
