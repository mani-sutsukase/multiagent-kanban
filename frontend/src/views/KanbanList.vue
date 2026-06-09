<template>
  <div class="kanban-list-page">
    <div class="page-header">
      <h1>看板列表</h1>
      <div class="header-actions">
        <button class="btn btn-outline" @click="triggerImport">↑ 导入</button>
        <button class="btn btn-primary" @click="showCreate = true">+ 新建看板</button>
        <input
          ref="fileInputRef"
          type="file"
          accept=".json,application/json"
          style="display: none"
          @change="onFileSelected"
        />
      </div>
    </div>

    <div v-if="kanbanStore.loading" class="loading">加载中...</div>

    <div v-else-if="kanbanStore.kanbans.length === 0" class="empty">
      <p>还没有看板，点击上方按钮创建一个</p>
    </div>

    <div v-else class="kanban-grid">
      <div
        v-for="kanban in kanbanStore.kanbans"
        :key="kanban.id"
        class="kanban-card"
        @click="$router.push(`/kanban/${kanban.id}`)"
      >
        <h3>{{ kanban.name }}</h3>
        <p v-if="kanban.description" class="desc">{{ kanban.description }}</p>
        <div class="meta">
          <span>{{ kanban.swimlanes?.length || 0 }} 个泳道</span>
        </div>
      </div>
    </div>

    <CreateKanbanDialog v-if="showCreate" @close="showCreate = false" @created="onCreated" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useKanbanStore } from '../stores/kanban'
import CreateKanbanDialog from '../components/CreateKanbanDialog.vue'
import { kanbanApi } from '../api/kanban'

const kanbanStore = useKanbanStore()
const showCreate = ref(false)
const fileInputRef = ref(null)
const importing = ref(false)

onMounted(() => {
  kanbanStore.fetchAll()
})

function onCreated() {
  showCreate.value = false
}

function triggerImport() {
  fileInputRef.value?.click()
}

async function onFileSelected(event) {
  const file = event.target.files?.[0]
  if (!file) return

  importing.value = true
  try {
    const text = await file.text()
    const data = JSON.parse(text)

    if (!data.kanban || !data.kanban.name) {
      throw new Error('无效的配置文件：缺少 kanban.name')
    }
    if (!Array.isArray(data.swimlanes)) {
      throw new Error('无效的配置文件：缺少 swimlanes 数组')
    }

    const res = await kanbanApi.importKanban(data)
    await kanbanStore.fetchAll()
    alert(`看板「${res.data.name}」导入成功（${res.data.swimlane_count} 个泳道）`)
  } catch (e) {
    alert('导入失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    importing.value = false
    event.target.value = ''
  }
}
</script>

<style scoped>
.kanban-list-page {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

h1 {
  font-size: 24px;
  color: #2c3e50;
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.kanban-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.kanban-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  transition: transform 0.2s, box-shadow 0.2s;
}

.kanban-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.kanban-card h3 {
  font-size: 16px;
  margin-bottom: 8px;
  color: #2c3e50;
}

.desc {
  color: #7f8c8d;
  font-size: 13px;
  margin-bottom: 12px;
}

.meta {
  font-size: 12px;
  color: #95a5a6;
}

.loading, .empty {
  text-align: center;
  padding: 60px 20px;
  color: #95a5a6;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}

.btn-primary {
  background: #3498db;
  color: #fff;
}

.btn-primary:hover {
  background: #2980b9;
}

.btn-outline {
  background: #fff;
  border: 1px solid #ddd;
  color: #555;
}

.btn-outline:hover {
  background: #f5f5f5;
}
</style>
