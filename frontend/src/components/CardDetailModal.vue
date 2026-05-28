<template>
  <div class="dialog-overlay" @click.self="$emit('close')">
    <div class="dialog dialog-lg">
      <div class="detail-header">
        <h2>{{ card.title }}</h2>
        <span class="status-badge" :class="card.status">{{ statusLabel }}</span>
      </div>

      <div class="detail-section">
        <div class="detail-field">
          <label>内容</label>
          <p>{{ card.content || '(无)' }}</p>
        </div>
        <div class="detail-field">
          <label>模型</label>
          <p>{{ card.model }}</p>
        </div>
        <div v-if="card.rejection_note" class="detail-field">
          <label>驳回批注</label>
          <p class="rejection-note">{{ card.rejection_note }}</p>
        </div>
        <div v-if="currentSessionId" class="detail-field">
          <label>Claude Session</label>
          <p class="session-id">{{ currentSessionId }}</p>
        </div>
      </div>

      <div class="status-action-section">
        <label>状态修改</label>
        <div class="status-action-row">
          <select v-model="newStatus" class="status-select">
            <option value="pending">待执行</option>
            <option value="running">执行中</option>
            <option value="blocked">异常</option>
            <option value="completed">已完成</option>
          </select>
          <button class="btn btn-primary" :disabled="changingStatus" @click="handleStatusChange">
            {{ changingStatus ? '修改中...' : '修改状态' }}
          </button>
        </div>
        <p v-if="changeError" class="status-error">{{ changeError }}</p>
      </div>

      <div v-if="logs.length > 0" class="timeline-section">
        <h3>执行时间线</h3>
        <LogTimeline :logs="logs" :swimlane-names="swimlaneNames" />
      </div>

      <div v-if="isRunning" class="live-indicator">
        <span class="live-dot"></span> 日志实时更新中...
      </div>

      <div class="dialog-actions">
        <button class="btn btn-cancel" @click="$emit('close')">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { logApi } from '../api/log'
import { cardApi } from '../api/card'
import LogTimeline from './LogTimeline.vue'

const props = defineProps({
  card: Object,
})

const emit = defineEmits(['close', 'status-changed'])

const logs = ref([])
const newStatus = ref(props.card.status)
const changingStatus = ref(false)
const changeError = ref('')
let pollTimer = null

const statusLabel = computed(() => {
  const labels = {
    pending: '待执行', running: '执行中', waiting_approval: '待审批',
    approved: '已批准', rejected: '已驳回', completed: '已完成', blocked: '异常',
  }
  return labels[props.card.status] || props.card.status
})

const isRunning = computed(() => props.card.status === 'running')

const currentSessionId = computed(() => {
  // 取最近一条有 session_id 的日志
  for (let i = logs.value.length - 1; i >= 0; i--) {
    if (logs.value[i].session_id) return logs.value[i].session_id
  }
  return null
})

const swimlaneNames = computed(() => {
  const names = {}
  for (const log of logs.value) {
    if (!names[log.swimlane_id]) {
      names[log.swimlane_id] = log.swimlane_id.substring(0, 8)
    }
  }
  return names
})

async function fetchLogs() {
  try {
    const res = await logApi.list(props.card.id)
    if (res.data) {
      logs.value = res.data
    }
  } catch (e) {
    console.error('加载日志失败:', e)
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(fetchLogs, 2000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function handleStatusChange() {
  changingStatus.value = true
  changeError.value = ''
  try {
    await cardApi.update(props.card.id, { status: newStatus.value })
    props.card.status = newStatus.value
    emit('status-changed', { id: props.card.id, status: newStatus.value })
  } catch (e) {
    changeError.value = e.response?.data?.detail || '修改状态失败'
  } finally {
    changingStatus.value = false
  }
}

// 卡片状态变化时自动启停轮询
watch(() => props.card.status, (newVal) => {
  if (newVal === 'running') {
    startPolling()
  } else {
    stopPolling()
  }
})

onMounted(async () => {
  await fetchLogs()
  if (props.card.status === 'running') {
    startPolling()
  }
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.dialog-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.dialog-lg { background: #fff; border-radius: 12px; padding: 24px; width: 680px; max-width: 90vw; max-height: 80vh; overflow-y: auto; }
.detail-header { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
h2 { font-size: 18px; color: #2c3e50; }
.status-badge { font-size: 12px; padding: 3px 10px; border-radius: 10px; }
.status-badge.completed { background: #d5f5e3; color: #27ae60; }
.status-badge.running { background: #d6eaf8; color: #2980b9; }
.status-badge.waiting_approval { background: #fef9e7; color: #f39c12; }
.status-badge.blocked { background: #fadbd8; color: #e74c3c; }
.detail-section { margin-bottom: 20px; }
.detail-field { margin-bottom: 12px; }
.detail-field label { font-size: 12px; color: #95a5a6; display: block; margin-bottom: 4px; }
.detail-field p { font-size: 14px; color: #2c3e50; }
.rejection-note { color: #e74c3c !important; background: #fef9e7; padding: 8px; border-radius: 6px; }
.session-id { font-family: monospace; font-size: 13px; color: #8e44ad !important; background: #f4ecf7; padding: 6px 10px; border-radius: 6px; display: inline-block; }
.live-indicator { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #2980b9; margin-bottom: 12px; }
.live-dot { width: 8px; height: 8px; border-radius: 50%; background: #2980b9; animation: pulse 1.5s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
.timeline-section { margin-bottom: 20px; }
.timeline-section h3 { font-size: 14px; color: #555; margin-bottom: 12px; }
.log-section { margin-bottom: 16px; }
.dialog-actions { display: flex; justify-content: flex-end; margin-top: 16px; }
.btn { padding: 8px 20px; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; }
.btn-cancel { background: #ecf0f1; color: #555; }
.btn-primary { background: #3498db; color: #fff; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.status-action-section { margin-bottom: 20px; padding: 12px; background: #f8f9fa; border-radius: 8px; }
.status-action-section > label { font-size: 12px; color: #95a5a6; display: block; margin-bottom: 6px; }
.status-action-row { display: flex; gap: 8px; align-items: center; }
.status-select { flex: 1; padding: 8px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
.status-error { color: #e74c3c; font-size: 13px; margin-top: 6px; }
</style>
