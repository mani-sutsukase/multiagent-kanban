<template>
  <div class="dialog-overlay" @click.self="$emit('close')">
    <div class="dialog">
      <h2>驳回批注</h2>
      <p class="hint">请提供驳回原因，Agent 将根据批注改进后重新执行</p>
      <div class="form-group">
        <textarea v-model="note" placeholder="请输入驳回原因..." rows="4" required></textarea>
      </div>
      <div class="dialog-actions">
        <button class="btn btn-cancel" @click="$emit('close')">取消</button>
        <button class="btn btn-danger" @click="confirm" :disabled="!note.trim()">确认驳回</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['close', 'confirm'])
const note = ref('')

function confirm() {
  if (!note.value.trim()) return
  emit('confirm', note.value.trim())
}
</script>

<style scoped>
.dialog-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.dialog { background: #fff; border-radius: 12px; padding: 24px; width: 440px; max-width: 90vw; }
h2 { margin-bottom: 8px; font-size: 18px; color: #2c3e50; }
.hint { font-size: 13px; color: #95a5a6; margin-bottom: 16px; }
.form-group textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; outline: none; resize: vertical; }
.form-group textarea:focus { border-color: #e74c3c; }
.dialog-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
.btn { padding: 8px 20px; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; }
.btn-danger { background: #e74c3c; color: #fff; }
.btn-danger:disabled { background: #fadbd8; cursor: not-allowed; }
.btn-cancel { background: #ecf0f1; color: #555; }
</style>
