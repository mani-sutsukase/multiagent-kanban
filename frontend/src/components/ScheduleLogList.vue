<template>
  <div class="dialog-overlay" @click.self="$emit('close')">
    <div class="dialog">
      <h2>{{ schedule.name }} - 执行历史</h2>

      <div v-if="loading" class="loading">加载中...</div>

      <div v-else-if="logs.length === 0" class="empty">暂无执行记录</div>

      <div v-else class="log-list">
        <div v-for="log in logs" :key="log.id" class="log-item">
          <div class="log-time">{{ formatTime(log.triggered_at) }}</div>
          <span class="log-status" :class="log.status">
            {{ log.status === 'success' ? '✓ 成功' : '✗ 失败' }}
          </span>
          <span v-if="log.created_card_id" class="log-card-id">
            卡片: {{ log.created_card_id.substring(0, 8) }}...
          </span>
          <span v-if="log.error_message" class="log-error">{{ log.error_message }}</span>
        </div>
      </div>

      <div class="dialog-actions">
        <button class="btn btn-cancel" @click="$emit('close')">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { scheduleApi } from '../api/schedule'

const props = defineProps({
  schedule: Object,
})

defineEmits(['close'])

const logs = ref([])
const loading = ref(true)

function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN')
}

onMounted(async () => {
  try {
    const res = await scheduleApi.logs(props.schedule.id)
    logs.value = res.data
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.dialog-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.dialog { background: #fff; border-radius: 12px; padding: 24px; width: 560px; max-width: 90vw; max-height: 70vh; overflow-y: auto; }
h2 { margin-bottom: 16px; font-size: 16px; color: #2c3e50; }
.log-list { display: flex; flex-direction: column; gap: 8px; }
.log-item { display: flex; align-items: center; gap: 12px; padding: 10px; background: #f8f9fa; border-radius: 8px; font-size: 13px; flex-wrap: wrap; }
.log-time { color: #95a5a6; min-width: 140px; }
.log-status { font-weight: 600; }
.log-status.success { color: #27ae60; }
.log-status.failed { color: #e74c3c; }
.log-card-id { color: #3498db; font-size: 12px; }
.log-error { color: #e74c3c; font-size: 12px; width: 100%; }
.loading, .empty { text-align: center; padding: 30px; color: #95a5a6; }
.dialog-actions { display: flex; justify-content: flex-end; margin-top: 16px; }
.btn { padding: 8px 20px; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; }
.btn-cancel { background: #ecf0f1; color: #555; }
</style>
