<template>
  <div class="approval-page">
    <div class="page-header">
      <h1>审批面板</h1>
      <span class="count-badge">待审批: {{ approvalStore.pendingCount }}</span>
    </div>

    <div v-if="approvalStore.loading" class="loading">加载中...</div>

    <div v-else-if="approvalStore.pendingList.length === 0" class="empty">
      暂无待审批的卡片
    </div>

    <div v-else class="pending-list">
      <div
        v-for="item in groupedByKanban"
        :key="item.kanban_id"
        class="kanban-group"
      >
        <h3 class="group-title">{{ item.kanban_name }}</h3>
        <div
          v-for="card in item.cards"
          :key="card.card_id"
          class="approval-card"
          :class="{ selected: selectedCard?.card_id === card.card_id }"
          @click="selectCard(card)"
        >
          <div class="card-header">
            <span class="card-title">{{ card.card_title }}</span>
            <span class="swimlane-tag">{{ card.swimlane_name }}</span>
          </div>
          <div class="card-time">{{ formatTime(card.created_at) }}</div>
        </div>
      </div>
    </div>

    <ApprovalDetail
      v-if="selectedCard"
      :approval-item="selectedCard"
      @close="selectedCard = null"
      @approved="onAction"
      @rejected="onAction"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useApprovalStore } from '../stores/approval'
import ApprovalDetail from '../components/ApprovalDetail.vue'

const approvalStore = useApprovalStore()
const selectedCard = ref(null)

const groupedByKanban = computed(() => {
  const groups = {}
  for (const item of approvalStore.pendingList) {
    if (!groups[item.kanban_id]) {
      groups[item.kanban_id] = { kanban_id: item.kanban_id, kanban_name: item.kanban_name, cards: [] }
    }
    groups[item.kanban_id].cards.push(item)
  }
  return Object.values(groups)
})

function selectCard(card) {
  selectedCard.value = card
}

function onAction() {
  selectedCard.value = null
  approvalStore.fetchPending()
}

function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN')
}

onMounted(() => {
  approvalStore.fetchPending()
})
</script>

<style scoped>
.approval-page { padding: 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
h1 { font-size: 24px; color: #2c3e50; }
.count-badge { background: #e74c3c; color: #fff; padding: 4px 12px; border-radius: 12px; font-size: 14px; }
.pending-list { display: flex; flex-direction: column; gap: 20px; }
.kanban-group { background: #fff; border-radius: 12px; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.group-title { font-size: 15px; color: #2c3e50; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #eee; }
.approval-card { padding: 12px; border-radius: 8px; cursor: pointer; transition: background 0.2s; margin-bottom: 4px; }
.approval-card:hover { background: #f0f7ff; }
.approval-card.selected { background: #e8f4fd; }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.card-title { font-size: 14px; font-weight: 500; color: #2c3e50; }
.swimlane-tag { font-size: 11px; padding: 2px 8px; border-radius: 10px; background: #fef9e7; color: #f39c12; }
.card-time { font-size: 12px; color: #95a5a6; }
.loading, .empty { text-align: center; padding: 60px; color: #95a5a6; }
</style>
