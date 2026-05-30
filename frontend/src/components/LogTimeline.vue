<template>
  <div class="timeline">
    <div
      v-for="log in logs"
      :key="log.id"
      class="timeline-item"
      :class="{ expanded: expandedId === log.id }"
    >
      <div class="timeline-dot" :class="dotClass(log)"></div>
      <div class="timeline-body">
        <div class="timeline-header-row" @click="toggleExpand(log.id)">
          <div class="timeline-header">
            <span class="attempt-badge">第 {{ log.attempt }} 次</span>
            <span class="swimlane-name">{{ swimlaneName(log) }}</span>
            <span v-if="log.exit_code !== null" class="exit-tag" :class="log.exit_code === 0 ? 'ok' : 'fail'">
              exit {{ log.exit_code }}
            </span>
          </div>
          <div class="timeline-meta">
            <span class="timeline-time">{{ formatTime(log.started_at) }}</span>
            <span class="expand-icon">{{ expandedId === log.id ? '\u25B2' : '\u25BC' }}</span>
          </div>
        </div>

        <div v-if="expandedId === log.id" class="log-content">
          <div v-if="log.prompt" class="log-block">
            <div class="log-block-header prompt-header">发送给 Claude 的提示词</div>
            <pre class="log-output prompt-output">{{ log.prompt }}</pre>
          </div>
          <div v-if="log.stdout" class="log-block">
            <div class="log-block-header stdout-header">stdout</div>
            <pre class="log-output">{{ log.stdout }}</pre>
          </div>
          <div v-if="log.stderr" class="log-block">
            <div class="log-block-header stderr-header">stderr</div>
            <pre class="log-output stderr">{{ log.stderr }}</pre>
          </div>
          <div v-if="!log.stdout && !log.stderr" class="log-empty">(无输出)</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  logs: Array,
  swimlaneNames: Object,
})

const expandedId = ref(props.logs?.length > 0 ? props.logs[props.logs.length - 1].id : null)

function toggleExpand(id) {
  expandedId.value = expandedId.value === id ? null : id
}

function dotClass(log) {
  if (log.exit_code === null) return 'running'
  return log.exit_code === 0 ? 'success' : 'fail'
}

function swimlaneName(log) {
  return props.swimlaneNames?.[log.swimlane_id] || log.swimlane_id.substring(0, 8)
}

function formatTime(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}
</script>

<style scoped>
.timeline {
  border-left: 2px solid #e0e0e0;
  padding-left: 20px;
}

.timeline-item {
  position: relative;
  margin-bottom: 8px;
  border-radius: 8px;
  background: #f8f9fa;
  overflow: hidden;
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

.timeline-dot.success { background: #27ae60; }
.timeline-dot.fail { background: #e74c3c; }
.timeline-dot.running {
  background: #3498db;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.timeline-body {
  transition: background 0.2s;
}

.timeline-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  cursor: pointer;
  user-select: none;
}

.timeline-item.expanded .timeline-header-row {
  background: #eef2f7;
  border-bottom: 1px solid #e0e0e0;
}

.timeline-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.attempt-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 6px;
  background: #eaf2f8;
  color: #2980b9;
  font-weight: 600;
}

.swimlane-name {
  font-size: 13px;
  color: #2c3e50;
}

.exit-tag {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.exit-tag.ok { color: #27ae60; background: #d5f5e3; }
.exit-tag.fail { color: #e74c3c; background: #fadbd8; }

.timeline-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.timeline-time {
  font-size: 11px;
  color: #95a5a6;
}

.expand-icon {
  font-size: 10px;
  color: #bbb;
}

/* Log content */
.log-content {
  padding: 0 14px 10px;
}

.log-block {
  margin-top: 8px;
}

.log-block-header {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 4px 4px 0 0;
  font-family: monospace;
}

.stdout-header {
  color: #2c3e50;
  background: #e8e8e8;
}

.stderr-header {
  color: #e74c3c;
  background: #fce8e6;
}

.prompt-header {
  color: #2980b9;
  background: #d6eaf8;
}

.log-output {
  margin: 0;
  padding: 12px 14px;
  background: #1e1e2e;
  color: #cdd6f4;
  font-size: 13px;
  line-height: 1.6;
  border-radius: 0 0 6px 6px;
  max-height: 300px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: 'Consolas', 'Courier New', monospace;
}

.prompt-output {
  max-height: 400px;
  background: #f8f9fa;
  color: #2c3e50;
  border: 1px solid #d6eaf8;
  border-top: none;
}

.stderr {
  border-left: 3px solid #e74c3c;
}

.log-empty {
  padding: 12px;
  color: #95a5a6;
  font-size: 12px;
  text-align: center;
}
</style>
