<template>
  <div class="swimlane-column">
    <div class="swimlane-header">
      <span class="swimlane-name">{{ swimlane.name }}</span>
      <span class="flow-badge" :class="swimlane.flow_mode">{{ flowLabel }}</span>
    </div>

    <div
      class="cards-container"
      :class="{ 'drag-over': isDragOver }"
      @dragover.prevent="onDragOver"
      @dragenter.prevent="onDragEnter"
      @dragleave="onDragLeave"
      @drop="onDrop"
    >
      <div v-if="!kanbanCards || kanbanCards.length === 0" class="empty-cards">
        暂无卡片
      </div>
      <CardItem
        v-for="card in kanbanCards"
        :key="card.id"
        :card="card"
        @click="showCardDetail(card)"
        @terminated="(cardId) => $emit('cardMoved', { cardId })"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useCardStore } from '../stores/card'
import CardItem from './CardItem.vue'

const props = defineProps({
  swimlane: Object,
  kanbanId: String,
})

const emit = defineEmits(['cardClick', 'cardMoved'])
const cardStore = useCardStore()

const isDragOver = ref(false)
let dragEnterCount = 0

function onDragOver(e) {
  e.dataTransfer.dropEffect = 'move'
}

function onDragEnter(e) {
  dragEnterCount++
  isDragOver.value = true
}

function onDragLeave(e) {
  dragEnterCount--
  if (dragEnterCount <= 0) {
    dragEnterCount = 0
    isDragOver.value = false
  }
}

async function onDrop(e) {
  isDragOver.value = false
  dragEnterCount = 0
  const cardId = e.dataTransfer.getData('text/plain')
  if (!cardId) return

  // 检查是否拖到了不同的泳道
  const allCards = cardStore.cards[props.kanbanId] || []
  const card = allCards.find((c) => c.id === cardId)
  if (!card || card.current_swimlane_id === props.swimlane.id) return

  try {
    await cardStore.move(cardId, props.swimlane.id)
    emit('cardMoved', { cardId, swimlaneId: props.swimlane.id })
  } catch (e) {
    console.error('移动卡片失败:', e)
  }
}

const flowLabel = computed(() => {
  const labels = { auto: '自动', pre_approval: '执行后审批', post_approval: '执行前审批' }
  return labels[props.swimlane.flow_mode] || props.swimlane.flow_mode
})

const kanbanCards = computed(() => {
  const allCards = cardStore.cards[props.kanbanId] || []
  return allCards.filter((c) => c.current_swimlane_id === props.swimlane.id)
})

function showCardDetail(card) {
  emit('cardClick', card)
}
</script>

<style scoped>
.swimlane-column {
  min-width: 310px;
  max-width: 360px;
  background: #f0f2f5;
  border-radius: 12px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  max-height: 100%;
}

.swimlane-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.swimlane-name {
  font-weight: 600;
  font-size: 14px;
  color: #2c3e50;
}

.flow-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
}

.flow-badge.auto { background: #d5f5e3; color: #27ae60; }
.flow-badge.pre_approval { background: #fef9e7; color: #f39c12; }
.flow-badge.post_approval { background: #ebdef0; color: #8e44ad; }

.cards-container {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: background-color 0.2s, border-color 0.2s;
  border-radius: 8px;
  padding: 4px;
  margin: -4px;
}

.cards-container.drag-over {
  background-color: #e8f4fd;
  border: 2px dashed #3498db;
  padding: 2px;
}

.empty-cards {
  text-align: center;
  padding: 24px;
  color: #bdc3c7;
  font-size: 13px;
}
</style>
