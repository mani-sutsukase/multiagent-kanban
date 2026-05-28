<template>
  <div class="dialog-overlay" @click.self="$emit('close')">
    <div class="dialog">
      <h2>泳道排序</h2>
      <p class="hint">拖拽调整泳道顺序</p>
      <div class="order-list">
        <div
          v-for="(swimlane, idx) in orderedSwimlanes"
          :key="swimlane.id"
          class="order-item"
          draggable="true"
          @dragstart="onDragStart(idx)"
          @dragover.prevent="onDragOver(idx)"
          @drop="onDrop"
        >
          <span class="drag-handle">⠿</span>
          <span class="order-num">{{ idx + 1 }}</span>
          <span class="order-name">{{ swimlane.name }}</span>
          <span class="flow-badge" :class="swimlane.flow_mode">{{ swimlane.flow_mode }}</span>
        </div>
      </div>
      <div class="dialog-actions">
        <button class="btn btn-cancel" @click="$emit('close')">取消</button>
        <button class="btn btn-primary" @click="save">保存排序</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useKanbanStore } from '../stores/kanban'

const props = defineProps({
  kanbanId: String,
  swimlanes: Array,
})

const emit = defineEmits(['close', 'updated'])
const kanbanStore = useKanbanStore()

const orderedSwimlanes = ref([...props.swimlanes].sort((a, b) => a.sort_order - b.sort_order))
let dragIdx = null

function onDragStart(idx) { dragIdx = idx }
function onDragOver(idx) {
  if (dragIdx === null || dragIdx === idx) return
  const item = orderedSwimlanes.value.splice(dragIdx, 1)[0]
  orderedSwimlanes.value.splice(idx, 0, item)
  dragIdx = idx
}
function onDrop() { dragIdx = null }

async function save() {
  await kanbanStore.reorderSwimlanes(props.kanbanId, orderedSwimlanes.value.map((s) => s.id))
  emit('updated')
}
</script>

<style scoped>
.dialog-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.dialog { background: #fff; border-radius: 12px; padding: 24px; width: 440px; max-width: 90vw; }
h2 { margin-bottom: 8px; font-size: 18px; color: #2c3e50; }
.hint { font-size: 13px; color: #95a5a6; margin-bottom: 16px; }
.order-list { display: flex; flex-direction: column; gap: 8px; }
.order-item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; background: #f8f9fa; border-radius: 8px; cursor: grab; }
.order-item:active { cursor: grabbing; }
.drag-handle { color: #bdc3c7; font-size: 18px; }
.order-num { font-weight: 600; color: #3498db; min-width: 20px; }
.order-name { flex: 1; font-size: 14px; color: #2c3e50; }
.flow-badge { font-size: 11px; padding: 2px 8px; border-radius: 10px; background: #f0f2f5; color: #7f8c8d; }
.dialog-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px; }
.btn { padding: 8px 20px; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; }
.btn-primary { background: #3498db; color: #fff; }
.btn-cancel { background: #ecf0f1; color: #555; }
</style>
