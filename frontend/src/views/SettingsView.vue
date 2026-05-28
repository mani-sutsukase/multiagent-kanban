<template>
  <div class="settings-page">
    <div class="page-header">
      <h1>系统设置</h1>
    </div>

    <div class="setting-card">
      <div class="setting-item">
        <div class="setting-info">
          <h3>卡片轮询间隔</h3>
          <p>后台扫描 pending 卡片并启动 Agent 执行的时间间隔（秒）。最小值 1 秒。</p>
        </div>
        <div class="setting-control">
          <input
            v-model.number="pollingInterval"
            type="number"
            min="1"
            max="300"
            class="interval-input"
          />
          <span class="unit">秒</span>
          <button class="btn btn-primary" @click="savePollingInterval" :disabled="saving">
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <div class="setting-card" style="margin-top: 16px;">
      <div class="setting-item" style="flex-direction: column;">
        <div class="setting-info" style="margin-bottom: 12px;">
          <h3>可用模型</h3>
          <p>创建卡片时可选的模型列表。留空则使用默认模型。</p>
        </div>
        <div class="models-list">
          <div v-for="(m, idx) in models" :key="idx" class="model-row">
            <input
              v-model="models[idx]"
              class="model-input"
              placeholder="claude-sonnet-4-20250514"
            />
            <button class="btn-icon btn-minus" @click="removeModel(idx)" title="删除">
              <span class="icon-text">−</span>
            </button>
            <button
              v-if="idx === models.length - 1"
              class="btn-icon btn-plus"
              @click="addModel"
              title="添加"
            >
              <span class="icon-text">+</span>
            </button>
          </div>
        </div>
        <div class="models-actions">
          <button class="btn btn-primary" @click="saveModels" :disabled="savingModels">
            {{ savingModels ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="saved" class="toast">设置已保存</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useSettingStore } from '../stores/setting'

const settingStore = useSettingStore()
const pollingInterval = ref(5)
const models = ref([])
const saving = ref(false)
const savingModels = ref(false)
const saved = ref(false)

onMounted(async () => {
  await settingStore.fetchAll()
  pollingInterval.value = parseInt(settingStore.get('polling_interval', '5'))
  const raw = settingStore.get('available_models', '')
  if (raw) {
    try {
      models.value = JSON.parse(raw)
    } catch {
      models.value = raw.split('\n').map(s => s.trim()).filter(s => s.length > 0)
    }
  }
  if (models.value.length === 0) {
    models.value.push('')
  }
})

async function savePollingInterval() {
  const val = Math.max(1, Math.floor(pollingInterval.value))
  pollingInterval.value = val
  saving.value = true
  try {
    await settingStore.update('polling_interval', String(val))
    saved.value = true
    setTimeout(() => { saved.value = false }, 2000)
  } finally {
    saving.value = false
  }
}

function addModel() {
  models.value.push('')
}

function removeModel(idx) {
  if (models.value.length > 1) {
    models.value.splice(idx, 1)
  }
}

async function saveModels() {
  savingModels.value = true
  try {
    const list = models.value.map(s => s.trim()).filter(s => s.length > 0)
    await settingStore.update('available_models', JSON.stringify(list))
    saved.value = true
    setTimeout(() => { saved.value = false }, 2000)
  } finally {
    savingModels.value = false
  }
}
</script>

<style scoped>
.settings-page {
  padding: 24px;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 24px;
  color: #2c3e50;
}

.setting-card {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  max-width: 600px;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
}

.setting-info h3 {
  font-size: 16px;
  color: #2c3e50;
  margin: 0 0 6px;
}

.setting-info p {
  font-size: 13px;
  color: #7f8c8d;
  margin: 0;
  line-height: 1.5;
}

.setting-control {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.interval-input {
  width: 80px;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 16px;
  text-align: center;
}

.unit {
  font-size: 14px;
  color: #7f8c8d;
}

.models-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.model-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.model-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
  font-family: 'Consolas', 'Courier New', monospace;
  outline: none;
}

.model-input:focus {
  border-color: #3498db;
}

.btn-icon {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.15s;
}

.btn-minus {
  background: #fadbd8;
  color: #e74c3c;
}

.btn-minus:hover {
  background: #f5b7b1;
}

.btn-plus {
  background: #d5f5e3;
  color: #27ae60;
}

.btn-plus:hover {
  background: #abebc6;
}

.icon-text {
  font-size: 18px;
  line-height: 1;
  font-weight: bold;
}

.models-actions {
  margin-top: 12px;
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

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  background: #27ae60;
  color: #fff;
  padding: 10px 24px;
  border-radius: 8px;
  font-size: 14px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  animation: fadeInOut 2s ease;
}

@keyframes fadeInOut {
  0% { opacity: 0; transform: translateX(-50%) translateY(10px); }
  15% { opacity: 1; transform: translateX(-50%) translateY(0); }
  85% { opacity: 1; transform: translateX(-50%) translateY(0); }
  100% { opacity: 0; transform: translateX(-50%) translateY(-10px); }
}
</style>
