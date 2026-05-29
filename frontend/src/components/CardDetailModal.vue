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
        <div v-if="card.result" class="detail-field">
          <label>执行结果</label>
          <div class="result-block" :class="isResultSuccess ? 'result-success' : 'result-error'">
            <div class="result-header">
              <span class="result-icon">{{ isResultSuccess ? '\u2713' : '\u2717' }}</span>
              <span class="result-label">{{ isResultSuccess ? '任务执行成功' : '任务执行失败' }}</span>
            </div>
            <div v-if="resultDetailText" class="result-detail">{{ resultDetailText }}</div>
          </div>
        </div>
        <div v-if="currentSessionId" class="detail-field">
          <label>Claude Session</label>
          <p class="session-id">{{ currentSessionId }}</p>
        </div>
      </div>

      <!-- 发送给 Claude 的提示词 -->
      <div v-if="card.last_prompt" class="detail-section prompt-section">
        <div class="section-title">
          <span class="section-icon">→</span>
          <label>发送给 Claude 的提示词</label>
          <button class="btn-copy" @click.stop="copyText(card.last_prompt)">复制</button>
        </div>
        <pre class="prompt-content">{{ card.last_prompt }}</pre>
      </div>

      <!-- Claude 的输出 -->
      <div v-if="card.last_output" class="detail-section output-section">
        <div class="section-title">
          <span class="section-icon">←</span>
          <label>Claude 的回复</label>
          <button class="btn-copy" @click.stop="copyText(card.last_output)">复制</button>
        </div>
        <pre class="output-content">{{ card.last_output }}</pre>
      </div>

      <!-- 用户回复区（waiting_for_reply 状态） -->
      <div v-if="card.status === 'waiting_for_reply'" class="detail-section reply-section">
        <label>回复 Claude</label>
        <textarea
          v-model="replyText"
          class="reply-textarea"
          placeholder="在此输入你要回复 Claude 的内容..."
          rows="4"
        ></textarea>
        <div class="reply-actions">
          <button
            class="btn btn-primary"
            :disabled="sendingReply || !replyText.trim()"
            @click="handleReply"
          >
            {{ sendingReply ? '发送中...' : '发送回复' }}
          </button>
          <button
            class="btn btn-success"
            :disabled="advancingCard"
            @click="handleAdvance"
          >
            {{ advancingCard ? '推进中...' : '推进到下一泳道' }}
          </button>
        </div>
        <p v-if="replyError" class="status-error">{{ replyError }}</p>
      </div>

      <div class="status-action-section">
        <label>状态修改</label>
        <div class="status-action-row">
          <select v-model="newStatus" class="status-select">
            <option value="pending">待执行</option>
            <option value="running">执行中</option>
            <option value="waiting_for_reply">待回复</option>
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
const replyText = ref('')
const sendingReply = ref(false)
const advancingCard = ref(false)
const replyError = ref('')
let pollTimer = null

const statusLabel = computed(() => {
  const labels = {
    pending: '待执行', running: '执行中', waiting_approval: '待审批',
    approved: '已批准', rejected: '已驳回', waiting_for_reply: '待回复',
    completed: '已完成', blocked: '异常',
  }
  return labels[props.card.status] || props.card.status
})

const isResultSuccess = computed(() => {
  if (!props.card.result) return false
  return props.card.result.startsWith('任务执行成功') || props.card.result.startsWith('任务已完成')
})

const isRunning = computed(() => props.card.status === 'running')

const resultDetailText = computed(() => {
  if (!props.card.result) return ''
  // 跳过第一行的标签（"任务执行成功/失败"），显示剩余完整内容
  const idx = props.card.result.indexOf('\n')
  return idx === -1 ? props.card.result : props.card.result.substring(idx + 1).trim()
})

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

async function handleReply() {
  if (!replyText.value.trim()) return
  sendingReply.value = true
  replyError.value = ''
  try {
    const res = await cardApi.reply(props.card.id, replyText.value.trim())
    // 更新本地 card 对象
    Object.assign(props.card, res.data)
    replyText.value = ''
    emit('status-changed', { id: props.card.id, status: 'pending' })
  } catch (e) {
    replyError.value = e.response?.data?.detail || '发送回复失败'
  } finally {
    sendingReply.value = false
  }
}

async function handleAdvance() {
  advancingCard.value = true
  replyError.value = ''
  try {
    const res = await cardApi.advance(props.card.id)
    Object.assign(props.card, res.data)
    emit('status-changed', { id: props.card.id, status: res.data.status })
  } catch (e) {
    replyError.value = e.response?.data?.detail || '推进失败'
  } finally {
    advancingCard.value = false
  }
}

function copyText(text) {
  navigator.clipboard.writeText(text || '').catch(() => {
    // 静默失败
  })
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
.status-badge.waiting_for_reply { background: #f4ecf7; color: #8e44ad; }
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

.result-block { padding: 10px 12px; border-radius: 8px; border: 1px solid transparent; }
.result-block.result-success { background: #f0faf4; border-color: #d5f5e3; }
.result-block.result-error { background: #fef5f5; border-color: #fadbd8; }
.result-block .result-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.result-block .result-icon { font-weight: 700; font-size: 16px; }
.result-block.result-success .result-icon { color: #27ae60; }
.result-block.result-error .result-icon { color: #e74c3c; }
.result-block .result-label { font-weight: 600; font-size: 14px; }
.result-block.result-success .result-label { color: #27ae60; }
.result-block.result-error .result-label { color: #e74c3c; }
.result-block .result-detail { margin-top: 6px; color: #555; font-family: monospace; font-size: 13px; white-space: pre-wrap; word-break: break-all; line-height: 1.5; max-height: 200px; overflow-y: auto; }

/* 提示词 / 输出区块 */
.section-title { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.section-title label { font-size: 12px; color: #95a5a6; margin-bottom: 0; }
.section-icon { font-weight: 700; font-size: 14px; color: #7f8c8d; }
.btn-copy { margin-left: auto; font-size: 11px; padding: 2px 8px; border: 1px solid #ddd; border-radius: 4px; background: #fff; color: #555; cursor: pointer; }
.btn-copy:hover { background: #f5f5f5; }

.prompt-content, .output-content {
  background: #f8f9fa; border: 1px solid #eee; border-radius: 8px;
  padding: 12px; font-family: monospace; font-size: 12px; line-height: 1.6;
  white-space: pre-wrap; word-break: break-all; color: #333;
  max-height: 300px; overflow-y: auto;
}
.prompt-content { border-left: 3px solid #3498db; }
.output-content { border-left: 3px solid #27ae60; }

/* 回复区 */
.reply-section { padding: 12px; background: #faf5ff; border: 1px solid #e8d5f5; border-radius: 8px; }
.reply-section > label { font-size: 12px; color: #8e44ad; display: block; margin-bottom: 6px; font-weight: 600; }
.reply-textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; font-family: inherit; resize: vertical; box-sizing: border-box; }
.reply-textarea:focus { border-color: #8e44ad; outline: none; box-shadow: 0 0 0 2px rgba(142, 68, 173, 0.15); }
.reply-actions { display: flex; gap: 8px; margin-top: 8px; }
.btn-success { background: #27ae60; color: #fff; }
.btn-success:disabled { opacity: 0.6; cursor: not-allowed; }

</style>
