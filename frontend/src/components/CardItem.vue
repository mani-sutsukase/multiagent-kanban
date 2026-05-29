<template>
  <div class="card-item" :class="card.status" @click="$emit('click')">
    <div class="card-title">{{ card.title }}</div>
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { logApi } from '../api/log'

const props = defineProps({
  card: Object,
})

defineEmits(['click'])

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
    blocked: '异常',
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
  if (!['completed', 'blocked', 'running'].includes(props.card.status)) return
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
</script>

<style scoped>
.card-item {
  background: #fff;
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  transition: box-shadow 0.2s;
}

.card-item:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}

.card-item.running {
  border-left: 3px solid #3498db;
}

.card-item.waiting_approval {
  border-left: 3px solid #f39c12;
}

.card-item.waiting_for_reply {
  border-left: 3px solid #8e44ad;
}

.card-item.completed {
  border-left: 3px solid #27ae60;
}

.card-item.blocked {
  border-left: 3px solid #e74c3c;
}

.card-title {
  font-size: 14px;
  font-weight: 500;
  color: #2c3e50;
  margin-bottom: 8px;
  word-break: break-all;
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
.status-badge.blocked { background: #fadbd8; color: #e74c3c; }

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
</style>
