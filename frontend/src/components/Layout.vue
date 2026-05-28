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
      <div class="countdown-section">
        <div class="countdown-divider"></div>
        <div class="countdown-label">⏱ {{ nearestSchedule ? '下一任务' : '检查轮询' }}</div>
        <div class="countdown-time">{{ countdownText }}</div>
        <div class="countdown-name">{{ nearestSchedule ? nearestSchedule.name : '等待定时任务...' }}</div>
      </div>
    </aside>
    <main class="main-content">
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

const approvalStore = useApprovalStore()
const cardStore = useCardStore()
const scheduleStore = useScheduleStore()
const settingStore = useSettingStore()
const { connect, on, off } = useWebSocket()

const countdownText = ref('00:05')
let countdownTimer = null
let refreshTimer = null
let pollSeconds = 5

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

  on('card_status_changed', (msg) => {
    cardStore.updateCardStatus(msg.card_id, msg.status, msg.swimlane_id)
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
</style>
