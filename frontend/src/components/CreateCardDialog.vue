<template>
  <div class="dialog-overlay" @click.self="$emit('close')">
    <div class="dialog">
      <h2>新建卡片</h2>
      <form @submit.prevent="submit">
        <div class="form-group">
          <label>标题 *</label>
          <input v-model="title" placeholder="例如：生成Q2市场报告" required />
        </div>
        <div class="form-group">
          <label>内容</label>
          <textarea v-model="content" placeholder="任务详细描述" rows="4"></textarea>
        </div>
        <div class="form-group">
          <label>模型</label>
          <div class="model-options">
            <label
              v-for="m in modelList"
              :key="m"
              class="model-radio"
              :class="{ selected: model === m }"
            >
              <input type="radio" v-model="model" :value="m" />
              <span class="radio-label">{{ m }}</span>
            </label>
          </div>
        </div>
        <div class="form-group">
          <label>目标泳道</label>
          <select v-model="targetSwimlaneId">
            <option :value="null">自动分配到第一个泳道</option>
            <option v-for="s in swimlanes" :key="s.id" :value="s.id">
              {{ s.name }}
            </option>
          </select>
        </div>
        <div class="dialog-actions">
          <button type="button" class="btn btn-cancel" @click="$emit('close')">取消</button>
          <button type="submit" class="btn btn-primary" :disabled="!title.trim()">创建</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useCardStore } from '../stores/card'
import { useSettingStore } from '../stores/setting'

const props = defineProps({
  kanbanId: String,
  swimlanes: Array,
})

const emit = defineEmits(['close', 'created'])
const cardStore = useCardStore()
const settingStore = useSettingStore()

const defaultModels = ['claude-sonnet-4-20250514', 'claude-opus-4-20250514', 'gpt-4o', 'o3-mini']

const modelList = computed(() => {
  const raw = settingStore.get('available_models', '')
  if (!raw) return defaultModels
  try {
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) && parsed.length > 0 ? parsed : defaultModels
  } catch {
    return defaultModels
  }
})

const title = ref('')
const content = ref('')
const model = ref('')
const targetSwimlaneId = ref(null)

// 当modelList就绪后设置默认选中
function setDefaultModel() {
  if (!model.value && modelList.value.length > 0) {
    model.value = modelList.value[0]
  }
}
setDefaultModel()

async function submit() {
  await cardStore.create(props.kanbanId, {
    title: title.value,
    content: content.value,
    model: model.value,
    target_swimlane_id: targetSwimlaneId.value,
  })
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
  width: 480px;
  max-width: 90vw;
}

h2 { margin-bottom: 20px; font-size: 18px; color: #2c3e50; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-size: 13px; color: #555; margin-bottom: 6px; }
.form-group input,
.form-group textarea,
.form-group select {
  width: 100%; padding: 8px 12px; border: 1px solid #ddd;
  border-radius: 8px; font-size: 14px; outline: none;
}
.form-group input:focus, .form-group textarea:focus, .form-group select:focus {
  border-color: #3498db;
}
.dialog-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px; }

.model-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.model-radio {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: 1px solid #ddd;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.15s;
  user-select: none;
}

.model-radio:hover {
  border-color: #3498db;
  background: #f0f8ff;
}

.model-radio.selected {
  border-color: #3498db;
  background: #eaf4fd;
  color: #2c3e50;
}

.model-radio input[type="radio"] {
  display: none;
}

.radio-label {
  white-space: nowrap;
}
.btn { padding: 8px 20px; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; }
.btn-primary { background: #3498db; color: #fff; }
.btn-primary:disabled { background: #bdc3c7; cursor: not-allowed; }
.btn-cancel { background: #ecf0f1; color: #555; }
</style>
