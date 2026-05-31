<template>
  <div class="log-manager">
    <div class="page-header">
      <h1>执行日志</h1>
      <div class="filter-bar">
        <select v-model="filterStatus" class="filter-select" @change="fetchData">
          <option value="">全部状态</option>
          <option value="completed">已完成</option>
          <option value="errored">异常</option>
          <option value="blocked">阻塞</option>
        </select>
        <button class="btn btn-outline" @click="fetchData">刷新</button>
      </div>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="items.length === 0" class="empty">
      暂无已完成的执行记录
    </div>

    <div v-else class="table-wrapper">
      <table class="log-table">
        <thead>
          <tr>
            <th>看板</th>
            <th>卡片标题</th>
            <th>泳道</th>
            <th>状态</th>
            <th>退出码</th>
            <th>执行时间</th>
            <th>Session</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.card_id">
            <td>{{ item.kanban_name }}</td>
            <td class="card-title">{{ item.card_title }}</td>
            <td>{{ swimlaneName(item) }}</td>
            <td>
              <span class="status-tag" :class="item.card_status">
                {{ item.card_status === 'completed' ? '已完成' : item.card_status === 'blocked' ? '阻塞' : '异常' }}
              </span>
            </td>
            <td>
              <span :class="exitCodeClass(item.exit_code)">{{ item.exit_code ?? '-' }}</span>
            </td>
            <td class="time-cell">{{ formatTime(item.started_at) }}</td>
            <td>
              <span v-if="item.session_id" class="session-id">{{ item.session_id.substring(0, 12) }}...</span>
              <span v-else class="no-session">-</span>
            </td>
            <td>
              <button class="btn btn-sm btn-primary" @click="viewDetail(item)">查看日志</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <LogDetailDialog
      v-if="selectedItem"
      :item="selectedItem"
      @close="selectedItem = null"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { logApi } from '../api/log'
import LogDetailDialog from '../components/LogDetailDialog.vue'

const loading = ref(false)
const items = ref([])
const filterStatus = ref('')
const selectedItem = ref(null)

async function fetchData() {
  loading.value = true
  try {
    const params = {}
    if (filterStatus.value) {
      params.status = filterStatus.value
    }
    const res = await logApi.cardSummary(params)
    items.value = res.data || []
  } catch (e) {
    console.error('加载日志列表失败:', e)
  } finally {
    loading.value = false
  }
}

function swimlaneName(item) {
  if (!item.swimlane_id) return '-'
  return item.swimlane_id.substring(0, 8)
}

function exitCodeClass(code) {
  if (code === null || code === undefined) return ''
  return code === 0 ? 'exit-ok' : 'exit-error'
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

function viewDetail(item) {
  selectedItem.value = item
}

onMounted(fetchData)
</script>

<style scoped>
.log-manager {
  padding: 24px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

h1 {
  font-size: 22px;
  color: #2c3e50;
  margin: 0;
}

.filter-bar {
  display: flex;
  gap: 8px;
  align-items: center;
}

.filter-select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  background: #fff;
}

.table-wrapper {
  flex: 1;
  overflow-y: auto;
}

.log-table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.log-table th {
  background: #f8f9fa;
  padding: 12px 16px;
  text-align: left;
  font-size: 13px;
  color: #666;
  font-weight: 600;
  border-bottom: 2px solid #eee;
}

.log-table td {
  padding: 12px 16px;
  font-size: 13px;
  color: #333;
  border-bottom: 1px solid #f0f0f0;
}

.log-table tr:hover {
  background: #f5f8ff;
}

.card-title {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-tag {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 10px;
  white-space: nowrap;
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

.time-cell {
  white-space: nowrap;
  font-size: 12px;
  color: #888;
}

.exit-ok {
  color: #27ae60;
  font-weight: 600;
}

.exit-error {
  color: #e74c3c;
  font-weight: 600;
}

.session-id {
  font-family: monospace;
  font-size: 12px;
  color: #8e44ad;
}

.no-session {
  color: #ccc;
}

.btn {
  padding: 8px 14px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  white-space: nowrap;
}

.btn-sm {
  padding: 5px 12px;
  font-size: 12px;
}

.btn-primary {
  background: #3498db;
  color: #fff;
}

.btn-outline {
  background: #fff;
  border: 1px solid #ddd;
  color: #555;
}

.loading,
.empty {
  text-align: center;
  padding: 60px;
  color: #95a5a6;
}
</style>
