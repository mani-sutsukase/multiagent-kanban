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
        <div class="form-group">
          <div class="collapse-header" @click="showPathConfig = !showPathConfig">
            <span>{{ showPathConfig ? '▾' : '▸' }} 路径配置</span>
            <span class="field-hint">设置 Claude 可访问的文件目录和权限</span>
          </div>
          <div v-if="showPathConfig" class="collapse-body">
            <div class="form-group">
              <label>工作目录</label>
              <div class="path-row">
                <input v-model="localPath" placeholder="例如 D:\my-project" />
                <button class="btn-sm btn-browse" type="button" @click="openWorkDirBrowser">选择</button>
              </div>
            </div>
            <div class="form-group">
              <label>目录权限</label>
              <select v-model="localPathPermission">
                <option value="read_write">读写权限</option>
                <option value="read_only">只读权限</option>
              </select>
            </div>
            <div class="form-group">
              <label>额外可访问路径</label>
              <div v-for="(ap, idx) in allowedPathsArr" :key="idx" class="extra-path-block">
                <div class="path-row">
                  <input v-model="ap.path" placeholder="例如 D:\other\project" />
                  <button class="btn-sm btn-browse" type="button" @click="openExtraPathBrowser(ap)">选择</button>
                </div>
                <div class="permission-row">
                  <select v-model="ap.permission" class="perm-select">
                    <option value="read_write">读写权限</option>
                    <option value="read_only">只读权限</option>
                  </select>
                  <button class="btn-sm btn-danger" type="button" @click="allowedPathsArr.splice(idx, 1)">×</button>
                </div>
              </div>
              <button class="btn-sm btn-browse" type="button" @click="allowedPathsArr.push({ path: '', permission: 'read_only' })">+ 添加路径</button>
            </div>
          </div>
        </div>
        <div class="form-group">
          <label class="checkbox-label">
            <input type="checkbox" v-model="skipPermissions" />
            <span class="checkbox-text">跳过文件权限限制 (<code>--dangerously-skip-permissions</code>)</span>
            <span class="field-hint">启用后 Claude 可读写项目根目录下任意文件（谨慎使用）</span>
          </label>
        </div>
        <div class="dialog-actions">
          <button type="button" class="btn btn-cancel" @click="$emit('close')">取消</button>
          <button type="submit" class="btn btn-primary" :disabled="!title.trim()">创建</button>
        </div>
      </form>
    </div>
  </div>

  <!-- 目录选择器弹窗 -->
  <div v-if="browserTarget" class="dialog-overlay browser-overlay" @click.self="browserTarget = null">
    <div class="dialog dialog-browser">
      <h2>选择目录</h2>
      <div class="browser-current-path">
        <input v-model="browserPath" class="browser-path-input" placeholder="输入路径后按 Enter" @keyup.enter="loadDir" />
        <button class="btn-sm btn-browse" @click="loadDir">转到</button>
      </div>
      <div v-if="browserError" class="browser-error">{{ browserError }}</div>
      <div class="browser-list">
        <div v-if="browserParent" class="browser-item browser-item-up" @click="browserPath = browserParent; loadDir()">
          <span class="browser-icon">📂</span>
          <span>.. (上级目录)</span>
        </div>
        <div
          v-for="entry in browserEntries"
          :key="entry.path"
          class="browser-item"
          :class="{ current: browserPath === entry.path }"
          @click="browserPath = entry.path; loadDir()"
        >
          <span class="browser-icon">📁</span>
          <span class="browser-name">{{ entry.name }}</span>
          <span class="browser-path-text">{{ entry.path }}</span>
        </div>
        <div v-if="browserEntries.length === 0 && !browserError" class="browser-empty">此目录下没有子目录</div>
      </div>
      <div class="browser-actions">
        <button class="btn btn-cancel" @click="browserTarget = null">取消</button>
        <button class="btn btn-primary" :disabled="!browserPath" @click="confirmDir">选择此文件夹</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useCardStore } from '../stores/card'
import { useSettingStore } from '../stores/setting'
import client from '../api/client'

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
const showPathConfig = ref(false)
const localPath = ref('')
const localPathPermission = ref('read_write')
const allowedPathsArr = ref([])
const skipPermissions = ref(false)

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
    local_path: localPath.value || null,
    local_path_permission: localPathPermission.value,
    allowed_paths: JSON.stringify(allowedPathsArr.value),
    dangerously_skip_permissions: skipPermissions.value,
  })
  emit('created')
}

// 目录浏览器状态
const browserTarget = ref(null)
const browserPath = ref('')
const browserParent = ref(null)
const browserEntries = ref([])
const browserError = ref('')

async function loadDir() {
  browserError.value = ''
  browserEntries.value = []
  try {
    const res = await client.get('/browse-directory', { params: { path: browserPath.value } })
    const data = res.data
    browserPath.value = data.current || ''
    browserParent.value = data.parent || null
    browserEntries.value = data.entries || []
    if (data.error) {
      browserError.value = data.error
    }
  } catch (e) {
    browserError.value = '无法读取目录'
  }
}

function openWorkDirBrowser() {
  browserTarget.value = { type: 'localPath' }
  browserPath.value = localPath.value || ''
  loadDir()
}

function openExtraPathBrowser(entry) {
  browserTarget.value = { type: 'extraPath', entry }
  browserPath.value = entry.path || ''
  loadDir()
}

function confirmDir() {
  if (!browserTarget.value || !browserPath.value) return
  if (browserTarget.value.type === 'localPath') {
    localPath.value = browserPath.value
  } else if (browserTarget.value.type === 'extraPath' && browserTarget.value.entry) {
    browserTarget.value.entry.path = browserPath.value
  }
  browserTarget.value = null
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
.collapse-header { display: flex; align-items: center; gap: 8px; cursor: pointer; padding: 8px 0; user-select: none; }
.collapse-header:hover { color: #3498db; }
.collapse-body { padding: 12px; background: #f8f9fa; border-radius: 8px; margin-top: 4px; }
.extra-path-block { margin-bottom: 10px; padding: 8px; background: #fff; border: 1px solid #eee; border-radius: 6px; }
.perm-select { font-size: 12px; padding: 3px 6px; border: 1px solid #ddd; border-radius: 4px; }
.btn-sm { padding: 4px 10px; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; }
.btn-danger { background: #fadbd8; color: #e74c3c; }
.btn-browse { background: #eaf2f8; color: #2980b9; white-space: nowrap; }
.field-hint { font-size: 11px; color: #95a5a6; }
.checkbox-label { display: flex; align-items: baseline; gap: 6px; flex-wrap: wrap; cursor: pointer; user-select: none; padding: 8px 12px; background: #fff8e1; border: 1px solid #ffe082; border-radius: 8px; }
.checkbox-label input[type="checkbox"] { cursor: pointer; }
.checkbox-text { font-size: 13px; color: #e67e22; font-weight: 600; }
.checkbox-text code { font-size: 12px; background: #fff3cd; padding: 1px 5px; border-radius: 3px; }
.checkbox-label .field-hint { width: 100%; margin-left: 20px; }
.btn { padding: 8px 20px; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; }
.btn-primary { background: #3498db; color: #fff; }
.btn-primary:disabled { background: #bdc3c7; cursor: not-allowed; }
.btn-cancel { background: #ecf0f1; color: #555; }

.path-row { display: flex; gap: 6px; }
.path-row input { flex: 1; }
.permission-row { display: flex; align-items: center; justify-content: space-between; margin-top: 4px; }

/* 目录浏览器 */
.browser-overlay { z-index: 200; }
.dialog-browser { width: 520px; max-height: 70vh; display: flex; flex-direction: column; }
.browser-current-path { display: flex; gap: 6px; margin-bottom: 12px; }
.browser-path-input { flex: 1; padding: 6px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 13px; outline: none; font-family: 'Consolas', 'Courier New', monospace; }
.browser-path-input:focus { border-color: #3498db; }
.browser-error { color: #e74c3c; font-size: 12px; margin-bottom: 8px; }
.browser-list { flex: 1; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 8px; min-height: 200px; max-height: 350px; background: #fafafa; }
.browser-item { display: flex; align-items: center; gap: 8px; padding: 8px 12px; cursor: pointer; border-bottom: 1px solid #eee; transition: background 0.1s; background: #fff; }
.browser-item:last-child { border-bottom: none; }
.browser-item:hover { background: #eef6fb; }
.browser-item.current { background: #e3f0fa; }
.browser-item-up { color: #7f8c8d; }
.browser-icon { font-size: 14px; flex-shrink: 0; }
.browser-name { font-size: 13px; color: #2c3e50; }
.browser-path-text { font-size: 11px; color: #95a5a6; margin-left: auto; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 200px; }
.browser-empty { padding: 24px; text-align: center; color: #95a5a6; font-size: 13px; }
.browser-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px; }
</style>
