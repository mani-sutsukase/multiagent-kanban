<template>
  <div class="kanban-view-page">
    <div class="page-header">
      <div>
        <button class="btn-back" @click="$router.push('/')">← 返回</button>
        <h1>{{ kanbanStore.currentKanban?.name || '看板详情' }}</h1>
      </div>
      <div class="header-actions">
        <button class="btn btn-outline" @click="showConfig = true">⚙ 泳道配置</button>
        <button class="btn btn-outline" @click="showOrder = true">↕ 排序</button>
        <button class="btn btn-outline" @click="showSettings = true">📝 设置</button>
        <button class="btn btn-primary" @click="showCreateCard = true">+ 新建卡片</button>
      </div>
    </div>

    <div v-if="kanbanStore.loading" class="loading">加载中...</div>

    <div v-else-if="!kanbanStore.currentKanban" class="empty">看板不存在</div>

    <div v-else class="swimlane-container">
      <SwimlaneColumn
        v-for="swimlane in swimlanes"
        :key="swimlane.id"
        :swimlane="swimlane"
        :kanban-id="route.params.id"
        @card-click="showCardDetail"
        @card-moved="onCardMoved"
      />
    </div>

    <CreateCardDialog
      v-if="showCreateCard"
      :kanban-id="route.params.id"
      :swimlanes="swimlanes"
      @close="showCreateCard = false"
      @created="onCardCreated"
    />
    <SwimlaneConfig
      v-if="showConfig"
      :kanban-id="route.params.id"
      :swimlanes="swimlanes"
      @close="showConfig = false"
      @updated="refresh"
    />
    <SwimlaneOrderEditor
      v-if="showOrder"
      :kanban-id="route.params.id"
      :swimlanes="swimlanes"
      @close="showOrder = false"
      @updated="refresh"
    />
    <KanbanSettings
      v-if="showSettings"
      :kanban="kanbanStore.currentKanban"
      @close="showSettings = false"
      @updated="refresh"
      @deleted="onDeleted"
    />

    <CardDetailModal
      v-if="selectedCard"
      :card="selectedCard"
      :swimlanes="swimlanes"
      @close="selectedCard = null"
      @status-changed="onCardStatusChanged"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useKanbanStore } from '../stores/kanban'
import { useCardStore } from '../stores/card'
import SwimlaneColumn from '../components/SwimlaneColumn.vue'
import CreateCardDialog from '../components/CreateCardDialog.vue'
import SwimlaneConfig from '../components/SwimlaneConfig.vue'
import SwimlaneOrderEditor from '../components/SwimlaneOrderEditor.vue'
import KanbanSettings from '../components/KanbanSettings.vue'
import CardDetailModal from '../components/CardDetailModal.vue'
import { cardApi } from '../api/card'

const route = useRoute()
const router = useRouter()
const kanbanStore = useKanbanStore()
const cardStore = useCardStore()

const showCreateCard = ref(false)
const showConfig = ref(false)
const showOrder = ref(false)
const showSettings = ref(false)
const selectedCard = ref(null)

const swimlanes = computed(() => kanbanStore.currentKanban?.swimlanes || [])

async function refresh() {
  await kanbanStore.fetchOne(route.params.id)
  await cardStore.fetchByKanban(route.params.id)
}

function onCardCreated() {
  showCreateCard.value = false
  cardStore.fetchByKanban(route.params.id)
}

function onDeleted() {
  router.push('/')
}

function showCardDetail(card) {
  // 直接使用 store 中的响应式卡片对象，WebSocket 推送后自动更新
  selectedCard.value = card
}

function onCardStatusChanged({ id, status }) {
  // 同步更新 store 中的卡片状态
  cardStore.updateCardStatus(id, status)
  // 刷新当前看板的卡片列表
  cardStore.fetchByKanban(route.params.id)
}

function onCardMoved() {
  // 拖拽移动卡片后刷新数据
  cardStore.fetchByKanban(route.params.id)
}

onMounted(refresh)
watch(() => route.params.id, refresh)
</script>

<style scoped>
.kanban-view-page {
  padding: 24px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.page-header > div:first-child {
  display: flex;
  align-items: center;
  gap: 12px;
}

h1 {
  font-size: 22px;
  color: #2c3e50;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.btn-back {
  background: none;
  border: none;
  font-size: 14px;
  color: #3498db;
  cursor: pointer;
}

.swimlane-container {
  display: flex;
  gap: 16px;
  flex: 1;
  overflow-x: auto;
  padding-bottom: 16px;
}

.btn {
  padding: 8px 14px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  white-space: nowrap;
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

.loading, .empty {
  text-align: center;
  padding: 60px;
  color: #95a5a6;
}
</style>
