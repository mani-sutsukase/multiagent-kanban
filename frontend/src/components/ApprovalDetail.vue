<template>
  <div class="dialog-overlay" @click.self="$emit('close')">
    <div class="dialog dialog-lg">
      <div class="detail-header">
        <h2>{{ approvalItem.card_title }}</h2>
        <span class="swimlane-badge">{{ approvalItem.swimlane_name }}</span>
      </div>

      <div v-if="logs.length > 0" class="log-section">
        <h3>Agent 执行日志</h3>
        <div class="log-tabs">
          <button
            :class="{ active: activeTab === 'stdout' }"
            @click="activeTab = 'stdout'"
          >stdout</button>
          <button
            :class="{ active: activeTab === 'stderr' }"
            @click="activeTab = 'stderr'"
          >stderr</button>
        </div>
        <div class="log-content" ref="logContainer">
          <pre>{{ activeTab === 'stdout' ? logStdout : logStderr }}</pre>
        </div>
      </div>

      <ApprovalActions
        :card-id="approvalItem.card_id"
        @approved="$emit('approved')"
        @rejected="$emit('rejected')"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { logApi } from '../api/log'
import ApprovalActions from './ApprovalActions.vue'

const props = defineProps({
  approvalItem: Object,
})

const emit = defineEmits(['close', 'approved', 'rejected'])

const logs = ref([])
const logStdout = ref('')
const logStderr = ref('')
const activeTab = ref('stdout')
const logContainer = ref(null)

async function fetchLogs() {
  try {
    const res = await logApi.list(props.approvalItem.card_id)
    logs.value = res.data
    if (props.approvalItem.log_id) {
      const log = logs.value.find((l) => l.id === props.approvalItem.log_id)
      if (log) {
        logStdout.value = log.stdout || '(empty)'
        logStderr.value = log.stderr || '(empty)'
      }
    } else if (logs.value.length > 0) {
      const last = logs.value[logs.value.length - 1]
      logStdout.value = last.stdout || '(empty)'
      logStderr.value = last.stderr || '(empty)'
    }
  } catch (e) {
    logStdout.value = '加载日志失败'
    logStderr.value = '加载日志失败'
  }
}

onMounted(fetchLogs)
</script>

<style scoped>
.dialog-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.dialog-lg { background: #fff; border-radius: 12px; padding: 24px; width: 700px; max-width: 90vw; max-height: 80vh; overflow-y: auto; }
.detail-header { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
h2 { font-size: 18px; color: #2c3e50; }
.swimlane-badge { font-size: 12px; padding: 3px 10px; border-radius: 10px; background: #fef9e7; color: #f39c12; }
.log-section { margin-bottom: 20px; }
.log-section h3 { font-size: 14px; color: #555; margin-bottom: 8px; }
.log-tabs { display: flex; gap: 4px; margin-bottom: 8px; }
.log-tabs button { padding: 4px 12px; border: 1px solid #ddd; border-radius: 6px; background: #f8f9fa; cursor: pointer; font-size: 12px; }
.log-tabs button.active { background: #3498db; color: #fff; border-color: #3498db; }
.log-content { background: #1e1e1e; color: #d4d4d4; border-radius: 8px; padding: 12px; max-height: 300px; overflow: auto; }
.log-content pre { margin: 0; font-size: 12px; line-height: 1.5; white-space: pre-wrap; word-break: break-all; }
</style>
