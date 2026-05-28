<template>
  <div class="dialog-overlay" @click.self="$emit('close')">
    <div class="dialog">
      <h2>新建看板</h2>
      <form @submit.prevent="submit">
        <div class="form-group">
          <label>看板名称 *</label>
          <input v-model="name" placeholder="例如：内容审核流水线" required />
        </div>
        <div class="form-group">
          <label>描述</label>
          <textarea v-model="description" placeholder="看板用途描述" rows="3"></textarea>
        </div>
        <div class="dialog-actions">
          <button type="button" class="btn btn-cancel" @click="$emit('close')">取消</button>
          <button type="submit" class="btn btn-primary" :disabled="!name.trim()">创建</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useKanbanStore } from '../stores/kanban'

const emit = defineEmits(['close', 'created'])
const kanbanStore = useKanbanStore()

const name = ref('')
const description = ref('')

async function submit() {
  await kanbanStore.create({ name: name.value, description: description.value })
  emit('created')
}
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.dialog {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  width: 440px;
  max-width: 90vw;
}

h2 {
  margin-bottom: 20px;
  font-size: 18px;
  color: #2c3e50;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 13px;
  color: #555;
  margin-bottom: 6px;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
}

.form-group input:focus,
.form-group textarea:focus {
  border-color: #3498db;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
}

.btn {
  padding: 8px 20px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}

.btn-primary {
  background: #3498db;
  color: #fff;
}

.btn-primary:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}

.btn-cancel {
  background: #ecf0f1;
  color: #555;
}
</style>
