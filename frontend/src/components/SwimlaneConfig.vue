<template>
  <div class="dialog-overlay" @click.self="$emit('close')">
    <div class="dialog dialog-lg">
      <h2>泳道配置</h2>

      <div class="swimlane-list">
        <div v-for="(swimlane, idx) in localSwimlanes" :key="swimlane.id" class="swimlane-config-item">
          <div class="config-header">
            <span class="config-index">#{{ idx + 1 }}</span>
            <input v-model="swimlane.name" class="name-input" placeholder="泳道名称" />
            <button class="btn-sm btn-danger" @click="deleteSwimlane(swimlane.id)" :disabled="deleting">删除</button>
          </div>

          <div class="config-body">
            <div class="form-group">
              <label>Prompt</label>
              <textarea v-model="swimlane.prompt" rows="3" placeholder="Agent 提示词"></textarea>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Skill</label>
                <input v-model="swimlane.skill" placeholder="可选 skill 名称" />
              </div>
              <div class="form-group">
                <label>流转模式</label>
                <select v-model="swimlane.flow_mode">
                  <option value="auto">全自动</option>
                  <option value="pre_approval">执行后审批</option>
                  <option value="post_approval">执行前审批</option>
                </select>
              </div>
              <div class="form-group">
                <label>泳道类型</label>
                <select v-model="swimlane.swimlane_type">
                  <option value="normal">普通泳道</option>
                  <option value="orchestrator">编排泳道</option>
                </select>
              </div>
            </div>
            <div class="form-group toggle-group">
              <label class="toggle-label">
                <span class="toggle-left">
                  <input type="checkbox" v-model="swimlane.wait_for_reply" true-value="1" false-value="0" class="toggle-input" />
                  <span class="toggle-switch"></span>
                  <span class="toggle-text">Claude 需要回复时等待</span>
                </span>
                <span class="field-hint">Claude 可输出 JSON 标记请求用户输入，卡片自动进入「待回复」状态</span>
              </label>
            </div>
            <div class="form-group">
              <label>本地工作目录</label>
              <div class="path-row">
                <input v-model="swimlane.local_path" placeholder="留空使用全局配置，例如 D:\my-project" />
                <button class="btn-sm btn-browse" type="button" @click="openBrowser(swimlane)">选择</button>
              </div>
              <div class="permission-row">
                <span class="field-hint">配置后将在该目录启动 Claude，使用该目录的 CLAUDE.md 等配置</span>
                <select v-model="swimlane.local_path_permission" class="permission-select">
                  <option value="read_write">读写权限</option>
                  <option value="read_only">只读权限</option>
                </select>
              </div>
            </div>
            <div class="form-group extra-paths">
              <label>额外可访问路径</label>
              <div v-for="(ap, apIdx) in swimlane.allowed_paths_arr" :key="apIdx" class="extra-path-block">
                <div class="path-row">
                  <input v-model="ap.path" placeholder="例如 D:\other\project" />
                  <button class="btn-sm btn-browse" type="button" @click="openExtraPathBrowser(ap)">选择</button>
                </div>
                <div class="permission-row">
                  <select v-model="ap.permission" class="permission-select">
                    <option value="read_write">读写权限</option>
                    <option value="read_only">只读权限</option>
                  </select>
                  <button class="btn-sm btn-danger" type="button" @click="removeExtraPath(swimlane, apIdx)">×</button>
                </div>
              </div>
              <button class="btn-sm btn-browse" type="button" @click="addExtraPath(swimlane)">+ 添加路径</button>
            </div>
          </div>
        </div>
      </div>

      <button class="btn btn-outline add-btn" @click="addSwimlane">+ 添加泳道</button>

      <div class="dialog-actions">
        <button class="btn btn-cancel" @click="$emit('close')">取消</button>
        <button class="btn btn-primary" @click="save">保存</button>
      </div>
    </div>
  </div>

  <!-- 目录选择器弹窗（独立 overlay，防止穿透） -->
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
import { ref } from 'vue'
import { useKanbanStore } from '../stores/kanban'
import client from '../api/client'

const props = defineProps({
  kanbanId: String,
  swimlanes: Array,
})

const emit = defineEmits(['close', 'updated'])
const kanbanStore = useKanbanStore()
const deleting = ref(false)

const localSwimlanes = ref(JSON.parse(JSON.stringify(props.swimlanes)))

// 为每个泳道初始化路径权限字段
localSwimlanes.value.forEach(sw => {
  if (!sw.local_path_permission) sw.local_path_permission = 'read_write'
  if (!sw.allowed_paths) sw.allowed_paths = '[]'
  if (!sw.wait_for_reply) sw.wait_for_reply = '1'
  parseAllowedPaths(sw)
})

// 路径权限工具函数
function parseAllowedPaths(sw) {
  try {
    const parsed = JSON.parse(sw.allowed_paths || '[]')
    sw.allowed_paths_arr = Array.isArray(parsed) ? parsed : []
  } catch {
    sw.allowed_paths_arr = []
  }
}

function serializeAllowedPaths(sw) {
  sw.allowed_paths = JSON.stringify(sw.allowed_paths_arr || [])
}

function addExtraPath(swimlane) {
  if (!swimlane.allowed_paths_arr) swimlane.allowed_paths_arr = []
  swimlane.allowed_paths_arr.push({ path: '', permission: 'read_only' })
}

function removeExtraPath(swimlane, idx) {
  swimlane.allowed_paths_arr.splice(idx, 1)
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

function openBrowser(swimlane) {
  browserTarget.value = swimlane
  browserPath.value = swimlane.local_path || ''
  loadDir()
}

function openExtraPathBrowser(entry) {
  browserTarget.value = entry
  browserPath.value = entry.path || ''
  loadDir()
}

function confirmDir() {
  if (browserTarget.value && browserPath.value) {
    if ('local_path' in browserTarget.value) {
      // 泳道对象：设置 local_path
      browserTarget.value.local_path = browserPath.value
    } else {
      // 额外路径条目：设置 path
      browserTarget.value.path = browserPath.value
    }
  }
  browserTarget.value = null
}

function addSwimlane() {
  localSwimlanes.value.push({
    id: '__new__' + Date.now(),
    name: '',
    prompt: '',
    skill: '',
    tools: '[]',
    swimlane_type: 'normal',
    flow_mode: 'auto',
    wait_for_reply: '1',
    local_path: '',
    local_path_permission: 'read_write',
    allowed_paths: '[]',
    allowed_paths_arr: [],
  })
}

async function deleteSwimlane(id) {
  if (id.startsWith('__new__')) {
    localSwimlanes.value = localSwimlanes.value.filter((s) => s.id !== id)
    return
  }
  deleting.value = true
  try {
    await kanbanStore.deleteSwimlane(id)
    localSwimlanes.value = localSwimlanes.value.filter((s) => s.id !== id)
  } finally {
    deleting.value = false
  }
}

async function save() {
  for (const s of localSwimlanes.value) {
    serializeAllowedPaths(s)
    if (s.id.startsWith('__new__')) {
      await kanbanStore.addSwimlane(props.kanbanId, {
        name: s.name,
        prompt: s.prompt,
        skill: s.skill || null,
        swimlane_type: s.swimlane_type || 'normal',
        flow_mode: s.flow_mode,
        local_path: s.local_path || null,
        wait_for_reply: s.wait_for_reply || '1',
        local_path_permission: s.local_path_permission || 'read_write',
        allowed_paths: s.allowed_paths || '[]',
      })
    } else {
      await kanbanStore.updateSwimlane(s.id, {
        name: s.name,
        prompt: s.prompt,
        skill: s.skill || null,
        swimlane_type: s.swimlane_type || 'normal',
        flow_mode: s.flow_mode,
        local_path: s.local_path || null,
        wait_for_reply: s.wait_for_reply || '1',
        local_path_permission: s.local_path_permission || 'read_write',
        allowed_paths: s.allowed_paths || '[]',
      })
    }
  }
  emit('updated')
}
</script>

<style scoped>
.dialog-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.dialog-lg { background: #fff; border-radius: 12px; padding: 24px; width: 1200px; max-width: 94vw; max-height: 85vh; overflow-y: auto; }
h2 { margin-bottom: 20px; font-size: 18px; color: #2c3e50; }
.swimlane-list { display: flex; flex-direction: column; gap: 16px; }
.swimlane-config-item { border: 1px solid #eee; border-radius: 8px; padding: 16px; }
.config-header { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.config-index { font-weight: 600; color: #3498db; font-size: 14px; }
.name-input { flex: 1; padding: 6px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
.config-body { padding-left: 4px; }
.form-group { margin-bottom: 12px; }
.form-group label { display: block; font-size: 12px; color: #555; margin-bottom: 4px; }
.form-group input, .form-group textarea, .form-group select {
  width: 100%; padding: 6px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 13px; outline: none;
}
.field-hint { display: block; font-size: 11px; color: #95a5a6; margin-top: 4px; }
.form-row { display: flex; gap: 12px; }
.form-row .form-group { flex: 1; }
.btn-sm { padding: 4px 10px; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; }
.btn-danger { background: #fadbd8; color: #e74c3c; }
.btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-browse { background: #eaf2f8; color: #2980b9; white-space: nowrap; }
.btn-browse:hover { background: #d4e6f1; }

/* 切换开关 — 左右分开 */
.toggle-group { margin-bottom: 8px; }
.toggle-label { display: flex; align-items: center; justify-content: space-between; cursor: pointer; user-select: none; padding: 8px 12px; background: #f8f9fa; border-radius: 8px; border: 1px solid #eee; }
.toggle-left { display: flex; align-items: center; gap: 10px; }
.toggle-input { display: none; }
.toggle-switch { position: relative; width: 36px; height: 20px; background: #ccc; border-radius: 10px; transition: background 0.2s; flex-shrink: 0; }
.toggle-switch::after { content: ''; position: absolute; top: 2px; left: 2px; width: 16px; height: 16px; background: #fff; border-radius: 50%; transition: transform 0.2s; }
.toggle-input:checked + .toggle-switch { background: #8e44ad; }
.toggle-input:checked + .toggle-switch::after { transform: translateX(16px); }
.toggle-text { font-size: 14px; color: #2c3e50; font-weight: 500; }
.toggle-label .field-hint { font-size: 12px; color: #95a5a6; text-align: right; }

.path-row { display: flex; gap: 6px; }
.path-row input { flex: 1; }
.permission-row { display: flex; align-items: center; justify-content: space-between; margin-top: 4px; }
.permission-select { font-size: 12px; padding: 3px 6px; border: 1px solid #ddd; border-radius: 4px; }
.extra-paths { margin-top: 8px; }
.extra-path-block { margin-bottom: 10px; padding: 8px; background: #fff; border: 1px solid #eee; border-radius: 6px; }

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
.add-btn { margin-top: 12px; width: 100%; }
.btn { padding: 8px 20px; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; }
.btn-primary { background: #3498db; color: #fff; }
.btn-cancel { background: #ecf0f1; color: #555; }
.btn-outline { background: #fff; border: 1px dashed #ddd; color: #555; padding: 10px; }
.dialog-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px; }
</style>
