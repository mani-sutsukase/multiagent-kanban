<template>
  <div class="dialog-overlay" @click.self="$emit('close')">
    <div class="dialog">
      <h2>{{ schedule ? '编辑定时任务' : '新建定时任务' }}</h2>
      <form @submit.prevent="submit">
        <div class="form-group">
          <label>名称 *</label>
          <input v-model="form.name" placeholder="例如：日报生成" required />
        </div>
        <div class="form-group">
          <label>描述</label>
          <textarea v-model="form.description" rows="2"></textarea>
        </div>
        <div class="form-group">
          <label>Cron 表达式 *</label>
          <input v-model="form.cron_expr" placeholder="例如：0 9 * * * (每天9点)" required />
          <span class="help">分 时 日 月 周 — 例如: 0 9 * * 1 (每周一9点)</span>
        </div>
        <div class="form-group">
          <label>卡片标题 *</label>
          <input v-model="form.card_title" placeholder="触发时创建的卡片标题" required />
        </div>
        <div class="form-group">
          <label>卡片内容</label>
          <textarea v-model="form.card_content" rows="3"></textarea>
        </div>
        <div class="form-group">
          <label>模型</label>
          <input v-model="form.card_model" placeholder="claude-sonnet-4-20250514" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>目标看板 ID *</label>
            <input v-model="form.target_kanban_id" required />
          </div>
          <div class="form-group">
            <label>目标泳道 ID *</label>
            <input v-model="form.target_swimlane_id" required />
          </div>
        </div>
        <div class="dialog-actions">
          <button type="button" class="btn btn-cancel" @click="$emit('close')">取消</button>
          <button type="submit" class="btn btn-primary">保存</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useScheduleStore } from '../stores/schedule'

const props = defineProps({
  schedule: Object,
})

const emit = defineEmits(['close', 'saved'])
const scheduleStore = useScheduleStore()

const form = reactive({
  name: props.schedule?.name || '',
  description: props.schedule?.description || '',
  cron_expr: props.schedule?.cron_expr || '',
  card_title: props.schedule?.card_title || '',
  card_content: props.schedule?.card_content || '',
  card_model: props.schedule?.card_model || 'claude-sonnet-4-20250514',
  target_kanban_id: props.schedule?.target_kanban_id || '',
  target_swimlane_id: props.schedule?.target_swimlane_id || '',
})

async function submit() {
  if (props.schedule) {
    await scheduleStore.update(props.schedule.id, form)
  } else {
    await scheduleStore.create(form)
  }
  emit('saved')
}
</script>

<style scoped>
.dialog-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.dialog { background: #fff; border-radius: 12px; padding: 24px; width: 520px; max-width: 90vw; max-height: 80vh; overflow-y: auto; }
h2 { margin-bottom: 20px; font-size: 18px; color: #2c3e50; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 13px; color: #555; margin-bottom: 4px; }
.form-group input, .form-group textarea { width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; outline: none; }
.form-group input:focus, .form-group textarea:focus { border-color: #3498db; }
.help { display: block; font-size: 11px; color: #95a5a6; margin-top: 4px; }
.form-row { display: flex; gap: 12px; }
.form-row .form-group { flex: 1; }
.dialog-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px; }
.btn { padding: 8px 20px; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; }
.btn-primary { background: #3498db; color: #fff; }
.btn-cancel { background: #ecf0f1; color: #555; }
</style>
