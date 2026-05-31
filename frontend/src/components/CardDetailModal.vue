<template>
  <div class="dialog-overlay" @click.self="$emit('close')">
    <div class="dialog dialog-lg">
      <!-- 顶部：标题 + 状态 -->
      <div class="detail-header">
        <div class="header-title-area">
          <h2 v-if="!editing" class="header-title">{{ card.title }}</h2>
          <input v-else v-model="editTitle" class="title-input" />
          <button v-if="!editing && card.status !== 'running'" class="btn-icon" @click="startEdit" title="编辑卡片">✏️</button>
        </div>
        <span class="status-badge" :class="card.status">{{ statusLabel }}</span>
      </div>

      <!-- 左右两栏布局 -->
      <div class="detail-body">
        <!-- 左栏：卡片信息 + 本泳道提示词/回复 -->
        <div class="detail-left">
          <div class="detail-section">
            <div class="detail-field">
              <label>内容</label>
              <p v-if="!editing">{{ card.content || '(无)' }}</p>
              <textarea v-else v-model="editContent" class="edit-textarea" rows="6" placeholder="输入卡片内容..."></textarea>
              <div v-if="editing" class="detail-field skip-perm-edit">
                <label class="checkbox-label">
                  <input type="checkbox" v-model="editSkipPermissions" />
                  <span class="checkbox-text">跳过文件权限限制</span>
                  <span class="field-hint">Claude 可读写项目根目录下任意文件（谨慎使用）</span>
                </label>
              </div>
            </div>
            <div class="detail-field">
              <label>模型</label>
              <p>{{ card.model }}</p>
            </div>
            <div v-if="card.rejection_note" class="detail-field">
              <label>驳回批注</label>
              <p class="rejection-note">{{ card.rejection_note }}</p>
            </div>
            <div v-if="card.result" class="detail-field">
              <label>执行结果</label>
              <div class="result-block" :class="isResultSuccess ? 'result-success' : 'result-error'">
                <div class="result-header">
                  <span class="result-icon">{{ isResultSuccess ? '\u2713' : '\u2717' }}</span>
                  <span class="result-label">{{ isResultSuccess ? '任务执行成功' : '任务执行失败' }}</span>
                </div>
                <div v-if="resultDetailText" class="result-detail">{{ resultDetailText }}</div>
              </div>
            </div>
            <div v-if="currentSessionId" class="detail-field">
              <label>Claude Session</label>
              <p class="session-id">{{ currentSessionId }}</p>
            </div>
            <div v-if="card.local_path || hasExtraPaths || card.dangerously_skip_permissions === '1'" class="detail-field">
              <label>文件访问路径</label>
              <div class="path-info">
                <div v-if="card.dangerously_skip_permissions === '1'" class="path-info-item">
                  <span class="path-info-label danger-badge">跳过文件权限限制</span>
                  <span class="path-info-value">Claude 可访问项目根目录下任意文件</span>
                </div>
                <div v-if="card.local_path" class="path-info-item">
                  <span class="path-info-label">工作目录：</span>
                  <span class="path-info-value">{{ card.local_path }}</span>
                  <span class="perm-badge" :class="card.local_path_permission || 'read_write'">
                    {{ (card.local_path_permission || 'read_write') === 'read_write' ? '读写' : '只读' }}
                  </span>
                </div>
                <div v-for="(ap, idx) in parsedAllowedPaths" :key="idx" class="path-info-item">
                  <span class="path-info-label">额外路径：</span>
                  <span class="path-info-value">{{ ap.path }}</span>
                  <span class="perm-badge" :class="ap.permission">
                    {{ ap.permission === 'read_write' ? '读写' : '只读' }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- 本泳道发送给 Claude 的提示词 -->
          <div v-if="card.last_prompt" class="detail-section prompt-section">
            <div class="section-title">
              <span class="section-icon">→</span>
              <label>发送给 Claude 的提示词</label>
              <button class="btn-copy" @click.stop="copyText(card.last_prompt)">复制</button>
            </div>
            <pre class="prompt-content">{{ card.last_prompt }}</pre>
          </div>

          <!-- 本泳道 Claude 的回复 -->
          <div v-if="card.last_output" class="detail-section output-section">
            <div class="section-title">
              <span class="section-icon">←</span>
              <label>Claude 的回复</label>
              <button class="btn-copy" @click.stop="copyText(card.last_output)">复制</button>
            </div>
            <pre class="output-content">{{ card.last_output }}</pre>
          </div>

          <!-- 用户回复区（waiting_for_reply 状态） -->
          <div v-if="card.status === 'waiting_for_reply'" class="detail-section reply-section">
            <!-- 上半部分：Claude 的提问 -->
            <div class="reply-question-area">
              <div class="reply-question-label-row">
                <span class="reply-section-icon">💬</span>
                <span>Claude 需要你回复</span>
              </div>
              <div class="reply-question">
                <p class="reply-question-text">{{ card.user_reply_question || card.last_output || '(无提问内容)' }}</p>
              </div>
            </div>
            <!-- 下半部分：用户回复输入 -->
            <div class="reply-input-area">
              <textarea
                v-model="replyText"
                class="reply-textarea"
                placeholder="在此输入你要回复 Claude 的内容..."
                rows="3"
              ></textarea>
              <div class="reply-actions">
                <button
                  class="btn btn-primary"
                  :disabled="sendingReply || !replyText.trim()"
                  @click="handleReply"
                >
                  {{ sendingReply ? '发送中...' : '发送回复' }}
                </button>
                <button
                  class="btn btn-advance"
                  :disabled="advancingCard"
                  @click="handleAdvance"
                >
                  {{ advancingCard ? '推进中...' : '推进到下一泳道' }}
                </button>
              </div>
              <p v-if="replyError" class="status-error">{{ replyError }}</p>
            </div>
          </div>

          <!-- 编辑模式操作按钮 -->
          <div v-if="editing" class="edit-actions">
            <button class="btn btn-cancel" @click="cancelEdit">取消</button>
            <button class="btn btn-primary" :disabled="savingEdit || !editTitle.trim()" @click="handleSaveEdit">
              {{ savingEdit ? '保存中...' : '保存修改' }}
            </button>
            <p v-if="editError" class="status-error">{{ editError }}</p>
          </div>

          <div class="dialog-actions">
            <button class="btn btn-cancel" @click="$emit('close')">关闭</button>
            <button class="btn btn-danger" @click="handleClean">
              清理执行记录
            </button>
          </div>
        </div>

        <!-- 右栏：状态 + 时间线 -->
        <div class="detail-right">
          <div class="status-action-section">
            <label>状态修改</label>
            <div class="status-action-row">
              <select v-model="newStatus" class="status-select">
                <option value="pending">待执行</option>
                <option value="running">执行中</option>
                <option value="waiting_for_reply">待回复</option>
                <option value="blocked">阻塞</option>
                <option value="errored">异常</option>
                <option value="completed">已完成</option>
              </select>
              <button class="btn btn-primary" :disabled="changingStatus" @click="handleStatusChange">
                {{ changingStatus ? '修改中...' : '修改状态' }}
              </button>
            </div>
            <p v-if="changeError" class="status-error">{{ changeError }}</p>
          </div>

          <div v-if="logs.length > 0" class="timeline-section">
            <h3>执行时间线</h3>
            <LogTimeline :logs="logs" :swimlane-names="swimlaneNames" />
          </div>

          <div v-if="isRunning" class="live-indicator">
            <span class="live-dot"></span> 日志实时更新中...
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { logApi } from '../api/log'
import { cardApi } from '../api/card'
import LogTimeline from './LogTimeline.vue'

const props = defineProps({
  card: Object,
  swimlanes: { type: Array, default: () => [] },
})

const emit = defineEmits(['close', 'status-changed'])

const logs = ref([])
const newStatus = ref(props.card.status)
const changingStatus = ref(false)
const changeError = ref('')
const replyText = ref('')
const sendingReply = ref(false)
const advancingCard = ref(false)
const replyError = ref('')
const editing = ref(false)
const editTitle = ref('')
const editContent = ref('')
const editSkipPermissions = ref(false)
const savingEdit = ref(false)
const editError = ref('')
let pollTimer = null

const statusLabel = computed(() => {
  const labels = {
    pending: '待执行', running: '执行中', waiting_approval: '待审批',
    approved: '已批准', rejected: '已驳回', waiting_for_reply: '待回复',
    completed: '已完成', blocked: '阻塞', errored: '异常',
  }
  return labels[props.card.status] || props.card.status
})

const isResultSuccess = computed(() => {
  if (!props.card.result) return false
  return props.card.result.startsWith('任务执行成功') || props.card.result.startsWith('任务已完成')
})

const isRunning = computed(() => props.card.status === 'running')

const resultDetailText = computed(() => {
  if (!props.card.result) return ''
  // 跳过第一行的标签（"任务执行成功/失败"），显示剩余完整内容
  const idx = props.card.result.indexOf('\n')
  return idx === -1 ? props.card.result : props.card.result.substring(idx + 1).trim()
})

const currentSessionId = computed(() => {
  // 取最近一条有 session_id 的日志
  for (let i = logs.value.length - 1; i >= 0; i--) {
    if (logs.value[i].session_id) return logs.value[i].session_id
  }
  return null
})

const swimlaneNames = computed(() => {
  const names = {}
  for (const sw of props.swimlanes) {
    names[sw.id] = sw.name
  }
  return names
})

const hasExtraPaths = computed(() => {
  return parsedAllowedPaths.value.length > 0
})

const parsedAllowedPaths = computed(() => {
  try {
    const raw = props.card.allowed_paths || '[]'
    return JSON.parse(raw)
  } catch {
    return []
  }
})

async function fetchLogs() {
  try {
    const res = await logApi.list(props.card.id)
    if (res.data) {
      logs.value = res.data
    }
  } catch (e) {
    console.error('加载日志失败:', e)
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(fetchLogs, 2000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function handleStatusChange() {
  changingStatus.value = true
  changeError.value = ''
  try {
    await cardApi.update(props.card.id, { status: newStatus.value })
    props.card.status = newStatus.value
    emit('status-changed', { id: props.card.id, status: newStatus.value })
  } catch (e) {
    changeError.value = e.response?.data?.detail || '修改状态失败'
  } finally {
    changingStatus.value = false
  }
}

async function handleReply() {
  if (!replyText.value.trim()) return
  sendingReply.value = true
  replyError.value = ''
  try {
    const res = await cardApi.reply(props.card.id, replyText.value.trim())
    // 更新本地 card 对象
    Object.assign(props.card, res.data)
    replyText.value = ''
    emit('status-changed', { id: props.card.id, status: 'pending' })
  } catch (e) {
    replyError.value = e.response?.data?.detail || '发送回复失败'
  } finally {
    sendingReply.value = false
  }
}

async function handleAdvance() {
  advancingCard.value = true
  replyError.value = ''
  try {
    const res = await cardApi.advance(props.card.id)
    Object.assign(props.card, res.data)
    emit('status-changed', { id: props.card.id, status: res.data.status })
  } catch (e) {
    replyError.value = e.response?.data?.detail || '推进失败'
  } finally {
    advancingCard.value = false
  }
}

function copyText(text) {
  navigator.clipboard.writeText(text || '').catch(() => {
    // 静默失败
  })
}

function startEdit() {
  editTitle.value = props.card.title
  editContent.value = props.card.content || ''
  editSkipPermissions.value = props.card.dangerously_skip_permissions === '1'
  editError.value = ''
  editing.value = true
}

function cancelEdit() {
  editing.value = false
  editTitle.value = ''
  editContent.value = ''
  editError.value = ''
}

async function handleSaveEdit() {
  const title = editTitle.value.trim()
  if (!title) return
  savingEdit.value = true
  editError.value = ''
  try {
    const res = await cardApi.update(props.card.id, {
      title,
      content: editContent.value,
      dangerously_skip_permissions: editSkipPermissions.value,
    })
    Object.assign(props.card, res.data)
    editing.value = false
    emit('status-changed', { id: props.card.id, status: props.card.status })
  } catch (e) {
    editError.value = e.response?.data?.detail || '保存失败'
  } finally {
    savingEdit.value = false
  }
}

async function handleClean() {
  if (!confirm('确定清理此卡片的所有执行记录？\n执行结果、日志、提示词和输出都将被清除，卡片将重置到第一泳道。')) return
  try {
    await cardApi.clean(props.card.id)
    props.card.status = 'pending'
    props.card.result = null
    props.card.last_prompt = null
    props.card.last_output = null
    props.card.rejection_note = null
    props.card.session_id = null
    props.card.user_reply_question = null
    logs.value = []
    emit('status-changed', { id: props.card.id, status: 'pending' })
  } catch (e) {
    alert('清理失败: ' + (e.response?.data?.detail || e.message))
  }
}

// 卡片状态变化时自动启停轮询
watch(() => props.card.status, (newVal) => {
  if (newVal === 'running') {
    startPolling()
  } else {
    stopPolling()
  }
})

onMounted(async () => {
  await fetchLogs()
  if (props.card.status === 'running') {
    startPolling()
  }
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.dialog-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.dialog-lg { background: #fff; border-radius: 12px; padding: 28px; width: 1265px; max-width: 96vw; max-height: 92vh; display: flex; flex-direction: column; overflow: hidden; }
.detail-header { display: flex; align-items: center; gap: 12px; margin-bottom: 24px; flex-shrink: 0; }
.header-title-area { display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0; }
.header-title { font-size: 20px; color: #2c3e50; margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.title-input { flex: 1; font-size: 18px; padding: 6px 10px; border: 1px solid #3498db; border-radius: 6px; outline: none; font-weight: 600; color: #2c3e50; }
.title-input:focus { box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2); }
.btn-icon { background: none; border: none; cursor: pointer; font-size: 16px; padding: 4px; border-radius: 4px; line-height: 1; opacity: 0.5; transition: opacity 0.2s; flex-shrink: 0; }
.btn-icon:hover { opacity: 1; background: #f0f2f5; }
.edit-textarea { width: 100%; padding: 10px; border: 1px solid #3498db; border-radius: 6px; font-size: 14px; font-family: inherit; resize: vertical; box-sizing: border-box; line-height: 1.6; }
.edit-textarea:focus { outline: none; box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2); }
.edit-actions { display: flex; gap: 8px; align-items: center; margin-top: 12px; }

/* 左右两栏布局 */
.detail-body { display: flex; gap: 24px; flex: 1; min-height: 0; overflow: hidden; }
.detail-left { flex: 7; overflow-y: auto; min-width: 0; padding-right: 4px; }
.detail-right { flex: 3; overflow-y: auto; min-width: 0; display: flex; flex-direction: column; gap: 16px; padding-left: 20px; border-left: 1px solid #e8e8e8; }

.status-badge { font-size: 12px; padding: 3px 10px; border-radius: 10px; }
.status-badge.completed { background: #d5f5e3; color: #27ae60; }
.status-badge.running { background: #d6eaf8; color: #2980b9; }
.status-badge.waiting_approval { background: #fef9e7; color: #f39c12; }
.status-badge.waiting_for_reply { background: #f4ecf7; color: #8e44ad; }
.status-badge.blocked { background: #fef9e7; color: #e67e22; }
.status-badge.errored { background: #fadbd8; color: #e74c3c; }
.detail-section { margin-bottom: 20px; }
.detail-field { margin-bottom: 12px; }
.detail-field label { font-size: 12px; color: #95a5a6; display: block; margin-bottom: 4px; }
.detail-field p { font-size: 14px; color: #2c3e50; }
.rejection-note { color: #e74c3c !important; background: #fef9e7; padding: 8px; border-radius: 6px; }
.session-id { font-family: monospace; font-size: 13px; color: #8e44ad !important; background: #f4ecf7; padding: 6px 10px; border-radius: 6px; display: inline-block; }
.detail-right .live-indicator { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #2980b9; }
.live-dot { width: 8px; height: 8px; border-radius: 50%; background: #2980b9; animation: pulse 1.5s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
.timeline-section h3 { font-size: 14px; color: #555; margin-bottom: 12px; }
.log-section { margin-bottom: 16px; }
.dialog-actions { display: flex; justify-content: space-between; margin-top: 16px; gap: 8px; }
.btn { padding: 8px 20px; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; }
.btn-cancel { background: #ecf0f1; color: #555; }
.btn-primary { background: #3498db; color: #fff; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.detail-right .status-action-section { padding: 12px; background: #f8f9fa; border-radius: 8px; }
.detail-right .timeline-section { margin-bottom: 0; }
.status-action-section > label { font-size: 12px; color: #95a5a6; display: block; margin-bottom: 6px; }
.status-action-row { display: flex; gap: 8px; align-items: center; }
.status-select { flex: 1; padding: 8px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
.status-error { color: #e74c3c; font-size: 13px; margin-top: 6px; }

.result-block { padding: 10px 12px; border-radius: 8px; border: 1px solid transparent; }
.result-block.result-success { background: #f0faf4; border-color: #d5f5e3; }
.result-block.result-error { background: #fef5f5; border-color: #fadbd8; }
.result-block .result-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.result-block .result-icon { font-weight: 700; font-size: 16px; }
.result-block.result-success .result-icon { color: #27ae60; }
.result-block.result-error .result-icon { color: #e74c3c; }
.result-block .result-label { font-weight: 600; font-size: 14px; }
.result-block.result-success .result-label { color: #27ae60; }
.result-block.result-error .result-label { color: #e74c3c; }
.result-block .result-detail { margin-top: 6px; color: #555; font-family: monospace; font-size: 13px; white-space: pre-wrap; word-break: break-all; line-height: 1.5; max-height: 200px; overflow-y: auto; }

.path-info { display: flex; flex-direction: column; gap: 4px; }
.path-info-item { display: flex; align-items: center; gap: 6px; font-size: 13px; flex-wrap: wrap; }
.path-info-label { color: #95a5a6; white-space: nowrap; }
.path-info-value { font-family: monospace; color: #2c3e50; word-break: break-all; }
.perm-badge { font-size: 11px; padding: 1px 6px; border-radius: 4px; font-weight: 600; white-space: nowrap; }
.perm-badge.read_write { color: #27ae60; background: #d5f5e3; }
.perm-badge.read_only { color: #e67e22; background: #fdebd0; }
.danger-badge { font-size: 11px; padding: 1px 6px; border-radius: 4px; font-weight: 600; white-space: nowrap; color: #e74c3c; background: #fadbd8; }

/* 提示词 / 输出区块 */
.section-title { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.section-title label { font-size: 12px; color: #95a5a6; margin-bottom: 0; }
.section-icon { font-weight: 700; font-size: 14px; color: #7f8c8d; }
.btn-copy { margin-left: auto; font-size: 11px; padding: 2px 8px; border: 1px solid #ddd; border-radius: 4px; background: #fff; color: #555; cursor: pointer; }
.btn-copy:hover { background: #f5f5f5; }

.prompt-content, .output-content {
  background: #f8f9fa; border: 1px solid #eee; border-radius: 8px;
  padding: 12px; font-family: monospace; font-size: 12px; line-height: 1.6;
  white-space: pre-wrap; word-break: break-all; color: #333;
  max-height: 300px; overflow-y: auto;
}
.prompt-content { border-left: 3px solid #3498db; }
.output-content { border-left: 3px solid #27ae60; }

/* 回复区 — 上下两层结构 */
.reply-section {
  display: flex; flex-direction: column;
  padding: 0; background: #faf5ff; border: 1px solid #e8d5f5; border-radius: 8px; overflow: hidden;
}
/* 上半部分：Claude 的提问 */
.reply-question-area {
  padding: 14px 16px 12px; border-bottom: 1px solid #e8d5f5;
}
.reply-question-label-row {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; color: #8e44ad; font-weight: 600; margin-bottom: 10px;
}
.reply-section-icon { font-size: 14px; }
.reply-question { background: #fff; border: 1px solid #d5b8e8; border-radius: 6px; padding: 10px 12px; }
.reply-question-text { font-size: 14px; color: #4a235a; margin: 0; line-height: 1.6; white-space: pre-wrap; }
/* 下半部分：用户回复输入 */
.reply-input-area {
  padding: 12px 16px 16px;
}
.reply-textarea {
  width: 100%; padding: 10px; border: 1px solid #d5b8e8; border-radius: 6px;
  font-size: 14px; font-family: inherit; resize: vertical; box-sizing: border-box;
  min-height: 72px; outline: none;
}
.reply-textarea:focus { border-color: #8e44ad; box-shadow: 0 0 0 2px rgba(142, 68, 173, 0.15); }
.reply-actions { display: flex; gap: 8px; margin-top: 10px; }
.btn-advance { background: #e8f5e9; color: #2e7d32; border: 1px solid #c8e6c9; }
.btn-advance:hover { background: #c8e6c9; }
.btn-advance:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-danger { background: #e74c3c; color: #fff; }
.btn-danger:hover { background: #c0392b; }

/* 编辑模式：跳过文件权限限制复选框 */
.skip-perm-edit { margin-top: 12px; }
.checkbox-label { display: flex; align-items: baseline; gap: 6px; flex-wrap: wrap; cursor: pointer; user-select: none; padding: 8px 12px; background: #fff8e1; border: 1px solid #ffe082; border-radius: 8px; }
.checkbox-label input[type="checkbox"] { cursor: pointer; }
.checkbox-text { font-size: 13px; color: #e67e22; font-weight: 600; }
.field-hint { font-size: 11px; color: #95a5a6; }
.checkbox-label .field-hint { width: 100%; margin-left: 20px; }

</style>
