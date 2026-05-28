<template>
  <div class="schedule-page">
    <div class="page-header">
      <h1>定时任务</h1>
      <button class="btn btn-primary" @click="showForm = true">+ 新建定时任务</button>
    </div>

    <div v-if="scheduleStore.loading" class="loading">加载中...</div>

    <div v-else-if="scheduleStore.schedules.length === 0" class="empty">
      暂无定时任务
    </div>

    <div v-else class="schedule-list">
      <div v-for="s in scheduleStore.schedules" :key="s.id" class="schedule-card">
        <div class="schedule-header">
          <h3>{{ s.name }}</h3>
          <label class="toggle">
            <input type="checkbox" :checked="s.enabled === 1" @change="toggle(s.id)" />
            <span class="toggle-slider"></span>
          </label>
        </div>
        <p v-if="s.description" class="desc">{{ s.description }}</p>
        <div class="schedule-meta">
          <span class="meta-item">⏰ {{ s.cron_expr }}</span>
          <span class="meta-item">📋 {{ s.card_title }}</span>
        </div>
        <div class="schedule-actions">
          <button class="btn-sm" @click="showLogs(s)">历史记录</button>
          <button class="btn-sm" @click="editSchedule(s)">编辑</button>
          <button class="btn-sm btn-danger-sm" @click="confirmDelete(s)">删除</button>
        </div>
      </div>
    </div>

    <ScheduleForm
      v-if="showForm"
      :schedule="editingSchedule"
      @close="closeForm"
      @saved="onSaved"
    />

    <ScheduleLogList
      v-if="showLogPanel"
      :schedule="logSchedule"
      @close="showLogPanel = false"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useScheduleStore } from '../stores/schedule'
import { scheduleApi } from '../api/schedule'
import ScheduleForm from '../components/ScheduleForm.vue'
import ScheduleLogList from '../components/ScheduleLogList.vue'

const scheduleStore = useScheduleStore()
const showForm = ref(false)
const showLogPanel = ref(false)
const editingSchedule = ref(null)
const logSchedule = ref(null)

onMounted(() => scheduleStore.fetchAll())

function toggle(id) {
  scheduleStore.toggle(id)
}

function editSchedule(s) {
  editingSchedule.value = s
  showForm.value = true
}

function showLogs(s) {
  logSchedule.value = s
  showLogPanel.value = true
}

function closeForm() {
  showForm.value = false
  editingSchedule.value = null
}

function onSaved() {
  closeForm()
  scheduleStore.fetchAll()
}

async function confirmDelete(s) {
  if (!confirm(`确定删除定时任务「${s.name}」？`)) return
  await scheduleStore.remove(s.id)
}
</script>

<style scoped>
.schedule-page { padding: 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
h1 { font-size: 24px; color: #2c3e50; }
.schedule-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.schedule-card { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.schedule-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.schedule-header h3 { font-size: 16px; color: #2c3e50; }
.desc { font-size: 13px; color: #7f8c8d; margin-bottom: 12px; }
.schedule-meta { display: flex; flex-direction: column; gap: 4px; margin-bottom: 12px; }
.meta-item { font-size: 12px; color: #95a5a6; }
.schedule-actions { display: flex; gap: 8px; justify-content: flex-end; border-top: 1px solid #eee; padding-top: 12px; }
.btn-sm { padding: 4px 12px; border: 1px solid #ddd; border-radius: 6px; background: #fff; cursor: pointer; font-size: 12px; }
.btn-danger-sm { color: #e74c3c; border-color: #fadbd8; }
.btn { padding: 8px 16px; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; }
.btn-primary { background: #3498db; color: #fff; }
.toggle { position: relative; display: inline-block; width: 40px; height: 22px; }
.toggle input { opacity: 0; width: 0; height: 0; }
.toggle-slider { position: absolute; cursor: pointer; inset: 0; background: #bdc3c7; border-radius: 22px; transition: 0.3s; }
.toggle-slider::before { content: ''; position: absolute; height: 16px; width: 16px; left: 3px; bottom: 3px; background: #fff; border-radius: 50%; transition: 0.3s; }
.toggle input:checked + .toggle-slider { background: #27ae60; }
.toggle input:checked + .toggle-slider::before { transform: translateX(18px); }
.loading, .empty { text-align: center; padding: 60px; color: #95a5a6; }
</style>
