<template>
  <div class="swimlane-column">
    <div class="swimlane-header">
      <span class="swimlane-name">{{ swimlane.name }}</span>
      <span class="flow-badge" :class="swimlane.flow_mode">{{ flowLabel }}</span>
    </div>

    <div class="cards-container">
      <div v-if="!kanbanCards || kanbanCards.length === 0" class="empty-cards">
        暂无卡片
      </div>
      <CardItem
        v-for="card in kanbanCards"
        :key="card.id"
        :card="card"
        @click="showCardDetail(card)"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useCardStore } from '../stores/card'
import CardItem from './CardItem.vue'

const props = defineProps({
  swimlane: Object,
  kanbanId: String,
})

const emit = defineEmits(['cardClick'])
const cardStore = useCardStore()

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
  min-width: 280px;
  max-width: 320px;
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
}

.empty-cards {
  text-align: center;
  padding: 24px;
  color: #bdc3c7;
  font-size: 13px;
}
</style>
