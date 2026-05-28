<template>
  <div class="dialog-overlay" @click.self="$emit('close')">
    <div class="dialog">
      <h2>看板设置</h2>
      <form @submit.prevent="save">
        <div class="form-group">
          <label>看板名称</label>
          <input v-model="form.name" required />
        </div>
        <div class="form-group">
          <label>描述</label>
          <textarea v-model="form.description" rows="3"></textarea>
        </div>
        <div class="dialog-actions">
          <button type="button" class="btn btn-danger" @click="confirmDelete">删除看板</button>
          <div>
            <button type="button" class="btn btn-cancel" @click="$emit('close')">取消</button>
            <button type="submit" class="btn btn-primary">保存</button>
          </div>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { useKanbanStore } from '../stores/kanban'

const props = defineProps({
  kanban: Object,
})

const emit = defineEmits(['close', 'updated', 'deleted'])
const kanbanStore = useKanbanStore()

const form = reactive({
  name: props.kanban.name,
  description: props.kanban.description,
})

async function save() {
  await kanbanStore.update(props.kanban.id, form)
  emit('updated')
}

async function confirmDelete() {
  if (!confirm(`确定删除看板「${props.kanban.name}」？所有泳道和卡片将被删除。`)) return
  await kanbanStore.remove(props.kanban.id)
  emit('deleted')
}
</script>

<style scoped>
.dialog-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.dialog { background: #fff; border-radius: 12px; padding: 24px; width: 440px; max-width: 90vw; }
h2 { margin-bottom: 20px; font-size: 18px; color: #2c3e50; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-size: 13px; color: #555; margin-bottom: 6px; }
.form-group input, .form-group textarea { width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; outline: none; }
.dialog-actions { display: flex; justify-content: space-between; align-items: center; margin-top: 20px; }
.dialog-actions > div { display: flex; gap: 8px; }
.btn { padding: 8px 20px; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; }
.btn-primary { background: #3498db; color: #fff; }
.btn-cancel { background: #ecf0f1; color: #555; }
.btn-danger { background: #fadbd8; color: #e74c3c; }
</style>
