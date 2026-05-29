<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="logo">MultiAgent</div>
      <nav class="nav">
        <router-link to="/" class="nav-item" :class="{ active: $route.path === '/' }">
          📋 看板
        </router-link>
        <router-link to="/approvals" class="nav-item" :class="{ active: $route.path.startsWith('/approvals') }">
          ✅ 审批
          <span v-if="approvalStore.pendingCount > 0" class="badge">{{ approvalStore.pendingCount }}</span>
        </router-link>
        <router-link to="/schedules" class="nav-item" :class="{ active: $route.path.startsWith('/schedules') }">
          ⏰ 定时任务
        </router-link>
        <router-link to="/logs" class="nav-item" :class="{ active: $route.path.startsWith('/logs') }">
          📄 日志
        </router-link>
        <router-link to="/settings" class="nav-item" :class="{ active: $route.path.startsWith('/settings') }">
          ⚙️ 设置
        </router-link>
      </nav>
      <div class="sidebar-footer">
        <div class="countdown-section">
          <div class="countdown-divider"></div>
          <div class="countdown-label">⏱ {{ nearestSchedule ? '下一任务' : '检查轮询' }}</div>
          <div class="countdown-time">{{ countdownText }}</div>
          <div class="countdown-name">{{ nearestSchedule ? nearestSchedule.name : '等待定时任务...' }}</div>
        </div>
        <div class="connection-section">
          <div class="connection-status" :class="{ disconnected: !isConnected }">
            <span class="connection-dot"></span>
            <span class="connection-text">{{ isConnected ? '已连接' : '已断开' }}</span>
          </div>
          <button class="btn-restart" :disabled="serverRestarting" @click="handleRestart">
            {{ serverRestarting ? '重启中...' : '重启服务器' }}
          </button>
        </div>
      </div>
    </aside>
    <main class="main-content">
      <!-- 断连遮罩 -->
      <div v-if="showDisconnectOverlay" class="disconnect-overlay">
        <div class="disconnect-card">
          <div class="disconnect-icon">⚠️</div>
          <div class="disconnect-title">服务器连接已断开</div>
          <div class="disconnect-desc">
            {{ serverRestarting ? '正在等待服务器重启，请稍候...' : '请检查服务器是否正常运行，或点击下方按钮重启' }}
          </div>
          <button
            v-if="!serverRestarting"
            class="btn btn-restart-lg"
            @click="handleRestart"
          >
            重启服务器
          </button>
          <div v-else class="restart-spinner">
            <span class="spinner"></span>
            <span>正在连接...</span>
          </div>
        </div>
      </div>
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useApprovalStore } from '../stores/approval'
import { useScheduleStore } from '../stores/schedule'
import { useSettingStore } from '../stores/setting'
import { useWebSocket } from '../composables/useWebSocket'
import { useCardStore } from '../stores/card'
import { useConnection } from '../composables/useConnection'

const approvalStore = useApprovalStore()
const cardStore = useCardStore()
const scheduleStore = useScheduleStore()
const settingStore = useSettingStore()
const { connect, on, off, connected: wsConnected } = useWebSocket()
const { apiConnected, serverRestarting, startHealthPing, restartServer } = useConnection()

const countdownText = ref('00:05')
let countdownTimer = null
let refreshTimer = null
let pollSeconds = 5

// 整体连接状态：API 和 WebSocket 都通才算已连接
const isConnected = computed(() => apiConnected.value && wsConnected.value)

// 断连遮罩：API 不通时显示
const showDisconnectOverlay = computed(() => !apiConnected.value)

function getPollInterval() {
  return parseInt(settingStore.get('polling_interval', '5')) || 5
}

const nearestSchedule = computed(() => {
  const enabled = scheduleStore.schedules.filter(
    (s) => s.enabled && s.next_run_time
  )
  if (enabled.length === 0) return null
  return enabled.reduce((nearest, s) => {
    const t = new Date(s.next_run_time).getTime()
    return t < new Date(nearest.next_run_time).getTime() ? s : nearest
  })
})

function updateCountdown() {
  const s = nearestSchedule.value
  if (!s) {
    // 无定时任务时，显示卡片轮询倒计时
    const interval = getPollInterval()
    if (pollSeconds > interval) pollSeconds = interval
    const mm = String(Math.floor(pollSeconds / 60)).padStart(2, '0')
    const ss = String(pollSeconds % 60).padStart(2, '0')
    countdownText.value = `${mm}:${ss}`
    pollSeconds--
    if (pollSeconds < 0) pollSeconds = interval
    return
  }
  // 恢复 pollSeconds，以便之后切换到轮询模式时使用正确间隔
  pollSeconds = getPollInterval()

  const diff = new Date(s.next_run_time).getTime() - Date.now()
  if (diff <= 0) {
    countdownText.value = '00:00'
    // 倒计时归零，刷新 store 获取新的 next_run_time
    scheduleStore.fetchAll()
    return
  }

  const totalSeconds = Math.floor(diff / 1000)
  const days = Math.floor(totalSeconds / 86400)
  const hours = Math.floor((totalSeconds % 86400) / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60

  const hh = String(hours).padStart(2, '0')
  const mm = String(minutes).padStart(2, '0')
  const ss = String(seconds).padStart(2, '0')

  if (days > 0) {
    countdownText.value = `${days}天 ${hh}:${mm}:${ss}`
  } else {
    countdownText.value = `${hh}:${mm}:${ss}`
  }
}

onMounted(async () => {
  approvalStore.fetchPending()
  scheduleStore.fetchAll()
  await settingStore.fetchAll()
  pollSeconds = getPollInterval()
  connect()
  startHealthPing()

  on('card_status_changed', (msg) => {
    cardStore.updateCardStatus(msg.card_id, msg.status, msg.swimlane_id, msg.result)
  })

  on('card_needs_approval', () => {
    approvalStore.fetchPending()
  })

  on('card_completed', () => {
    approvalStore.fetchPending()
  })

  // 倒计时每秒更新
  countdownTimer = setInterval(updateCountdown, 1000)
  // 每 60 秒刷新 store
  refreshTimer = setInterval(() => {
    scheduleStore.fetchAll()
    settingStore.fetchAll()
  }, 60000)
})

function handleRestart() {
  restartServer()
}

onUnmounted(() => {
  off('card_status_changed')
  off('card_needs_approval')
  off('card_completed')
  if (countdownTimer) clearInterval(countdownTimer)
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
}

.sidebar {
  width: 200px;
  background: #1a1a2e;
  color: #fff;
  display: flex;
  flex-direction: column;
  padding: 20px 0;
}

.logo {
  font-size: 1.2rem;
  font-weight: bold;
  padding: 0 20px 20px;
  border-bottom: 1px solid #333;
  margin-bottom: 20px;
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 0 12px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  color: #ccc;
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.nav-item.active {
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
  font-weight: 600;
}

.badge {
  background: #e74c3c;
  color: #fff;
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 10px;
  margin-left: auto;
}

.main-content {
  flex: 1;
  overflow-y: auto;
  background: #f5f6fa;
}

.countdown-section {
  padding: 12px 20px 0;
  margin-top: auto;
}

.countdown-divider {
  height: 1px;
  background: #333;
  margin-bottom: 12px;
}

.countdown-label {
  font-size: 12px;
  color: #999;
  margin-bottom: 4px;
}

.countdown-time {
  font-size: 26px;
  font-weight: bold;
  color: #e74c3c;
  font-family: 'Courier New', Courier, monospace;
  line-height: 1.2;
}

.countdown-name {
  font-size: 12px;
  color: #888;
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-footer {
  margin-top: auto;
  padding: 0 20px 16px;
}

.connection-section {
  padding-top: 12px;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.connection-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #27ae60;
  transition: background 0.3s;
}

.connection-status.disconnected .connection-dot {
  background: #e74c3c;
}

.connection-text {
  font-size: 12px;
  color: #999;
}

.connection-status.disconnected .connection-text {
  color: #e74c3c;
}

.btn-restart {
  width: 100%;
  padding: 6px 12px;
  border: 1px solid #555;
  border-radius: 6px;
  background: transparent;
  color: #ccc;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-restart:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: #888;
  color: #fff;
}

.btn-restart:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 断连遮罩 */
.disconnect-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
}

.disconnect-card {
  background: #fff;
  border-radius: 16px;
  padding: 40px;
  text-align: center;
  max-width: 400px;
}

.disconnect-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.disconnect-title {
  font-size: 20px;
  font-weight: 700;
  color: #2c3e50;
  margin-bottom: 12px;
}

.disconnect-desc {
  font-size: 14px;
  color: #666;
  margin-bottom: 24px;
  line-height: 1.6;
}

.btn-restart-lg {
  padding: 10px 32px;
  background: #3498db;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-restart-lg:hover {
  background: #2980b9;
}

.restart-spinner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #666;
  font-size: 14px;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 3px solid #ddd;
  border-top-color: #3498db;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
