<template>
  <div
    class="card-item"
    :class="[card.status, { dragging: isDragging }]"
    draggable="true"
    @click="$emit('click')"
    @dragstart="onDragStart"
    @dragend="onDragEnd"
  >
    <div class="card-title-row">
      <span class="card-title">{{ card.title }}</span>
      <button class="btn-delete-icon" @click.stop="handleDelete" :disabled="deleting" title="删除卡片">🗑️</button>
    </div>
    <div class="card-meta">
      <span class="status-badge" :class="card.status">{{ statusLabel }}</span>
      <span class="model">{{ card.model }}</span>
    </div>

    <!-- 日志预览区域：completed / blocked / running 状态显示 -->
    <div v-if="logPreview" class="log-preview" :class="logPreview.type" @click.stop>
      <div class="log-header">
        <span class="log-icon">{{ logPreview.icon }}</span>
        <span class="log-exit">exit: {{ logPreview.exitCode }}</span>
        <span v-if="logPreview.swimlane" class="log-swimlane">{{ logPreview.swimlane }}</span>
      </div>
      <div v-if="logPreview.text" class="log-text">{{ logPreview.text }}</div>
    </div>
    <div v-else-if="loadingLog" class="log-preview loading-log">
      <span class="log-text dim">加载日志...</span>
    </div>

    <!-- 执行结果详情：完成/异常状态显示 -->
    <div v-if="card.result" class="card-result" :class="resultClass" @click.stop>
      <div class="result-header">
        <span class="result-icon">{{ resultIcon }}</span>
        <span class="result-label">{{ resultLabel }}</span>
      </div>
      <div v-if="resultDetail" class="result-detail">{{ resultDetail }}</div>
    </div>

    <!-- 终止按钮：仅 running 状态显示 -->
    <button v-if="card.status === 'running'" class="btn-terminate" @click.stop="handleTerminate" :disabled="terminating">
      {{ terminating ? '终止中...' : '终止' }}
    </button>

    <!-- 删除按钮 -->
    <button class="btn-delete" @click.stop="handleDelete" :disabled="deleting">
      {{ deleting ? '删除中...' : '删除' }}
    </button>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { logApi } from '../api/log'
import { cardApi } from '../api/card'
import { useCardStore } from '../stores/card'

const props = defineProps({
  card: Object,
  kanbanId: String,
})

const emit = defineEmits(['click', 'terminated', 'deleted'])

const isDragging = ref(false)
const terminating = ref(false)
const deleting = ref(false)

async function handleTerminate() {
  if (terminating.value) return
  terminating.value = true
  try {
    await cardApi.terminate(props.card.id)
    props.card.status = 'blocked'
    props.card.result = '用户手动终止执行'
    emit('terminated', props.card.id)
  } catch (e) {
    console.error('终止失败:', e)
    alert('终止失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    terminating.value = false
  }
}

async function handleDelete() {
  if (deleting.value) return
  if (!confirm(`确定删除卡片「${props.card.title}」？\n此操作不可撤销，关联的日志和审批记录也将一并清除。`)) return
  deleting.value = true
  try {
    await cardApi.delete(props.card.id)
    const cardStore = useCardStore()
    if (props.kanbanId && cardStore.cards[props.kanbanId]) {
      cardStore.cards[props.kanbanId] = cardStore.cards[props.kanbanId].filter((c) => c.id !== props.card.id)
    }
    emit('deleted', props.card.id)
  } catch (e) {
    console.error('删除失败:', e)
    alert('删除失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    deleting.value = false
  }
}

function onDragStart(e) {
  isDragging.value = true
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('text/plain', props.card.id)
  // 让拖拽时显示半透明效果
  if (e.target) {
    e.target.style.opacity = '0.5'
  }
}

function onDragEnd(e) {
  isDragging.value = false
  if (e.target) {
    e.target.style.opacity = ''
  }
}

const logs = ref([])
const loadingLog = ref(false)

const statusLabel = computed(() => {
  const labels = {
    pending: '待执行',
    running: '执行中',
    waiting_approval: '待审批',
    waiting_for_reply: '待回复',
    approved: '已批准',
    rejected: '已驳回',
    completed: '已完成',
    blocked: '阻塞',
    errored: '异常',
  }
  return labels[props.card.status] || props.card.status
})

const logPreview = computed(() => {
  if (logs.value.length === 0) return null
  const last = logs.value[logs.value.length - 1]
  const exitOk = last.exit_code === 0
  const type = exitOk ? 'success' : 'error'
  const icon = exitOk ? '\u2713' : '\u2717'
  const exitCode = last.exit_code ?? '-'

  // 取 stdout/stderr 第一行作为预览
  const text = (last.stdout || last.stderr || '').split('\n')[0]?.trim() || ''
  const swimlane = last.swimlane_id ? last.swimlane_id.substring(0, 8) : null

  return { type, icon, exitCode, text, swimlane }
})

const resultClass = computed(() => {
  if (!props.card.result) return ''
  return props.card.result.startsWith('任务执行成功') || props.card.result.startsWith('任务已完成') ? 'result-success' : 'result-error'
})

const resultIcon = computed(() => {
  if (!props.card.result) return ''
  return props.card.result.startsWith('任务执行成功') || props.card.result.startsWith('任务已完成') ? '\u2713' : '\u2717'
})

const resultLabel = computed(() => {
  if (!props.card.result) return ''
  return props.card.result.startsWith('任务执行成功') || props.card.result.startsWith('任务已完成') ? '执行成功' : '执行失败'
})

const resultDetail = computed(() => {
  if (!props.card.result) return ''
  // 跳过第一行的标签（"执行成功/失败"），显示剩余完整内容
  const idx = props.card.result.indexOf('\n')
  return idx === -1 ? props.card.result : props.card.result.substring(idx + 1).trim()
})

async function fetchLogs() {
  if (!['completed', 'blocked', 'errored', 'running', 'waiting_for_reply'].includes(props.card.status)) return
  loadingLog.value = true
  try {
    const res = await logApi.list(props.card.id)
    logs.value = res.data || []
  } catch {
    // 静默失败
  } finally {
    loadingLog.value = false
  }
}

onMounted(fetchLogs)

// 状态变化时自动刷新日志预览
watch(() => props.card.status, (newStatus, oldStatus) => {
  if (newStatus !== oldStatus) {
    // 切换到 pending 时清除旧日志（卡片进入新泳道重新执行）
    if (newStatus === 'pending') {
      logs.value = []
    }
    fetchLogs()
  }
})
</script>

<style scoped>
.card-item {
  background: #fff;
  border-radius: 10px;
  padding: 14px 16px;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  transition: box-shadow 0.2s;
}

.card-item:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}

.card-item.dragging {
  opacity: 0.5;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.card-item.running {
  border-left: 4px solid #3498db;
}

.card-item.waiting_approval {
  border-left: 4px solid #f39c12;
}

.card-item.waiting_for_reply {
  border-left: 4px solid #8e44ad;
}

.card-item.completed {
  border-left: 4px solid #27ae60;
}

.card-item.blocked {
  border-left: 4px solid #e67e22;
}

.card-item.errored {
  border-left: 4px solid #e74c3c;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #2c3e50;
  word-break: break-all;
  flex: 1;
  min-width: 0;
}

.card-title-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 10px;
}

.btn-delete-icon {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  padding: 2px 4px;
  border-radius: 4px;
  line-height: 1;
  opacity: 0.4;
  transition: opacity 0.15s, background 0.15s;
  flex-shrink: 0;
  margin-top: 1px;
}
.btn-delete-icon:hover:not(:disabled) {
  opacity: 1;
  background: #fef5f5;
}
.btn-delete-icon:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.card-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.status-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
}

.status-badge.pending { background: #f0f2f5; color: #7f8c8d; }
.status-badge.running { background: #d6eaf8; color: #2980b9; }
.status-badge.waiting_approval { background: #fef9e7; color: #f39c12; }
.status-badge.waiting_for_reply { background: #f4ecf7; color: #8e44ad; }
.status-badge.approved { background: #d5f5e3; color: #27ae60; }
.status-badge.rejected { background: #fadbd8; color: #e74c3c; }
.status-badge.completed { background: #d5f5e3; color: #27ae60; }
.status-badge.blocked { background: #fef9e7; color: #e67e22; }
.status-badge.errored { background: #fadbd8; color: #e74c3c; }

.model {
  font-size: 11px;
  color: #95a5a6;
}

/* 日志预览 */
.log-preview {
  margin-top: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  font-size: 11px;
  line-height: 1.5;
  border: 1px solid transparent;
  cursor: default;
}

.log-preview.success {
  background: #f0faf4;
  border-color: #d5f5e3;
}

.log-preview.error {
  background: #fef5f5;
  border-color: #fadbd8;
}

.log-preview.loading-log {
  background: #f8f9fa;
}

.log-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 2px;
}

.log-icon {
  font-weight: 700;
  font-size: 13px;
}

.log-preview.success .log-icon { color: #27ae60; }
.log-preview.error .log-icon { color: #e74c3c; }

.log-exit {
  font-family: monospace;
  color: #7f8c8d;
}

.log-swimlane {
  font-family: monospace;
  color: #95a5a6;
  margin-left: auto;
}

.log-text {
  color: #555;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: monospace;
}

.log-text.dim {
  color: #95a5a6;
}

/* 执行结果 */
.card-result {
  margin-top: 6px;
  padding: 6px 8px;
  border-radius: 6px;
  font-size: 11px;
  line-height: 1.5;
  border: 1px solid transparent;
  cursor: default;
}

.card-result.result-success {
  background: #f0faf4;
  border-color: #d5f5e3;
}

.card-result.result-error {
  background: #fef5f5;
  border-color: #fadbd8;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 6px;
}

.result-icon {
  font-weight: 700;
  font-size: 13px;
}

.card-result.result-success .result-icon { color: #27ae60; }
.card-result.result-error .result-icon { color: #e74c3c; }

.result-label {
  font-weight: 600;
  font-size: 12px;
}

.card-result.result-success .result-label { color: #27ae60; }
.card-result.result-error .result-label { color: #e74c3c; }

.result-detail {
  margin-top: 4px;
  color: #555;
  font-family: monospace;
  font-size: 11px;
  word-break: break-all;
  white-space: pre-wrap;
  max-height: 60px;
  overflow-y: auto;
}

/* 终止按钮 */
.btn-terminate {
  margin-top: 8px;
  width: 100%;
  padding: 6px 0;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  background: #fadbd8;
  color: #e74c3c;
  transition: background 0.15s;
}
.btn-terminate:hover:not(:disabled) {
  background: #f5b7b1;
}
.btn-terminate:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 删除按钮 */
.btn-delete {
  margin-top: 6px;
  width: 100%;
  padding: 6px 0;
  border: 1px solid #f5c6cb;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  background: #fff5f5;
  color: #c82333;
  transition: background 0.15s, border-color 0.15s;
}
.btn-delete:hover:not(:disabled) {
  background: #f8d7da;
  border-color: #f5c6cb;
}
.btn-delete:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
