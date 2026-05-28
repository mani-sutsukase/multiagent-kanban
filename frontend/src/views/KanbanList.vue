<template>
  <div class="kanban-list-page">
    <div class="page-header">
      <h1>看板列表</h1>
      <button class="btn btn-primary" @click="showCreate = true">+ 新建看板</button>
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

const kanbanStore = useKanbanStore()
const showCreate = ref(false)

onMounted(() => {
  kanbanStore.fetchAll()
})

function onCreated() {
  showCreate.value = false
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
</style>
