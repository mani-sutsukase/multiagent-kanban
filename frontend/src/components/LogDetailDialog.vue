<template>
  <div class="dialog-overlay" @click.self="$emit('close')">
    <div class="dialog dialog-lg">
      <div class="header">
        <div class="header-info">
          <h2>{{ item.card_title }}</h2>
          <div class="header-meta">
            <span class="meta-tag kanban-tag">{{ item.kanban_name }}</span>
            <span class="status-tag" :class="item.card_status">
              {{ item.card_status === 'completed' ? '已完成' : item.card_status === 'blocked' ? '阻塞' : '异常' }}
            </span>
          </div>
        </div>
        <button class="btn-close" @click="$emit('close')">&times;</button>
      </div>

      <div v-if="loading" class="loading">加载日志中...</div>

      <template v-else>
        <!-- 执行时间线 -->
        <div v-if="logs.length > 0" class="section">
          <h3>执行时间线</h3>
          <div class="timeline">
            <div
              v-for="log in logs"
              :key="log.id"
              class="timeline-item"
              :class="{ active: selectedLogId === log.id }"
              @click="selectedLogId = log.id"
            >
              <div class="timeline-dot" :class="logDotClass(log)"></div>
              <div class="timeline-body">
                <div class="timeline-header">
                  <span class="attempt-badge">第 {{ log.attempt }} 次</span>
                  <span class="swimlane-id">{{ log.swimlane_id.substring(0, 8) }}</span>
                  <span v-if="log.exit_code !== null" class="exit-tag" :class="log.exit_code === 0 ? 'ok' : 'fail'">
                    exit {{ log.exit_code }}
                  </span>
                </div>
                <div class="timeline-time">{{ formatTime(log.started_at) }} ~ {{ formatTime(log.finished_at) }}</div>
                <div v-if="log.session_id" class="timeline-session">Session: {{ log.session_id }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 日志详情 -->
        <div v-if="selectedLog" class="section">
          <h3>标准输出 (stdout)</h3>
          <pre class="log-output">{{ selectedLog.stdout || '(无输出)' }}</pre>
        </div>

        <div v-if="selectedLog && selectedLog.stderr" class="section">
          <h3 class="stderr-title">错误输出 (stderr)</h3>
          <pre class="log-output stderr">{{ selectedLog.stderr }}</pre>
        </div>

        <div v-if="!logs.length" class="empty">暂无日志记录</div>
      </template>

      <div class="actions">
        <button class="btn btn-cancel" @click="$emit('close')">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { logApi } from '../api/log'

const props = defineProps({
  item: Object,
})

defineEmits(['close'])

const loading = ref(false)
const logs = ref([])
const selectedLogId = ref(null)

const selectedLog = computed(() => {
  if (!selectedLogId.value) return null
  return logs.value.find(l => l.id === selectedLogId.value) || null
})

function logDotClass(log) {
  if (log.exit_code === null) return 'running'
  return log.exit_code === 0 ? 'success' : 'fail'
}

function formatTime(t) {
  if (!t) return '-'
  try {
    const d = new Date(t)
    return d.toLocaleString('zh-CN', {
      month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    })
  } catch {
    return t
  }
}

async function fetchLogs() {
  loading.value = true
  try {
    const res = await logApi.list(props.item.card_id)
    logs.value = res.data || []
    if (logs.value.length > 0) {
      // 默认选中最后一条日志
      selectedLogId.value = logs.value[logs.value.length - 1].id
    }
  } catch (e) {
    console.error('加载日志详情失败:', e)
  } finally {
    loading.value = false
  }
}

onMounted(fetchLogs)
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}

.dialog-lg {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  width: 780px;
  max-width: 92vw;
  max-height: 85vh;
  overflow-y: auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.header-info h2 {
  font-size: 18px;
  color: #2c3e50;
  margin: 0 0 8px 0;
}

.header-meta {
  display: flex;
  gap: 8px;
  align-items: center;
}

.meta-tag {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 10px;
  background: #eaf2f8;
  color: #2980b9;
}

.status-tag {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 10px;
}

.status-tag.completed {
  background: #d5f5e3;
  color: #27ae60;
}

.status-tag.blocked {
  background: #fef9e7;
  color: #e67e22;
}

.status-tag.errored {
  background: #fadbd8;
  color: #e74c3c;
}

.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  color: #999;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
}

.btn-close:hover {
  color: #333;
}

.section {
  margin-bottom: 20px;
}

.section h3 {
  font-size: 14px;
  color: #555;
  margin: 0 0 10px 0;
}

/* Timeline */
.timeline {
  border-left: 2px solid #e0e0e0;
  padding-left: 20px;
}

.timeline-item {
  position: relative;
  padding: 10px 14px;
  margin-bottom: 8px;
  background: #f8f9fa;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.timeline-item:hover {
  background: #eef2f7;
}

.timeline-item.active {
  background: #e8f0fe;
  border: 1px solid #b3d4fc;
}

.timeline-dot {
  position: absolute;
  left: -27px;
  top: 14px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #ccc;
  border: 2px solid #fff;
}

.timeline-dot.success {
  background: #27ae60;
}

.timeline-dot.fail {
  background: #e74c3c;
}

.timeline-dot.running {
  background: #3498db;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.timeline-header {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 4px;
}

.attempt-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 6px;
  background: #eaf2f8;
  color: #2980b9;
  font-weight: 600;
}

.swimlane-id {
  font-family: monospace;
  font-size: 11px;
  color: #888;
}

.exit-tag {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.exit-tag.ok {
  color: #27ae60;
  background: #d5f5e3;
}

.exit-tag.fail {
  color: #e74c3c;
  background: #fadbd8;
}

.timeline-time {
  font-size: 12px;
  color: #888;
}

.timeline-session {
  font-size: 12px;
  color: #8e44ad;
  font-family: monospace;
  margin-top: 2px;
}

/* Log output */
.log-output {
  background: #1e1e2e;
  color: #cdd6f4;
  padding: 14px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.6;
  max-height: 300px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: 'Consolas', 'Courier New', monospace;
}

.stderr-title {
  color: #e74c3c !important;
}

.stderr {
  border-left: 3px solid #e74c3c;
}

.loading,
.empty {
  text-align: center;
  padding: 40px;
  color: #95a5a6;
}

.actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.btn {
  padding: 8px 20px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}

.btn-cancel {
  background: #ecf0f1;
  color: #555;
}
</style>
