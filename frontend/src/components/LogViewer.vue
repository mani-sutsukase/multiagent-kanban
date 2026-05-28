<template>
  <div class="log-viewer">
    <div class="log-tabs">
      <button :class="{ active: activeTab === 'stdout' }" @click="activeTab = 'stdout'">stdout</button>
      <button :class="{ active: activeTab === 'stderr' }" @click="activeTab = 'stderr'">stderr</button>
    </div>
    <div class="log-content" ref="logContainer">
      <pre><template v-for="(line, idx) in displayLines" :key="idx"><span class="line-num">{{ idx + 1 }}</span>{{ line }}<br /></template></pre>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue'

const props = defineProps({
  logs: Array,
  initialLogId: String,
})

const activeTab = ref('stdout')

const currentLog = computed(() => {
  if (props.initialLogId) {
    return props.logs.find((l) => l.id === props.initialLogId)
  }
  return props.logs[props.logs.length - 1] || null
})

const displayText = computed(() => {
  if (!currentLog.value) return ''
  return activeTab.value === 'stdout'
    ? (currentLog.value.stdout || '')
    : (currentLog.value.stderr || '')
})

const displayLines = computed(() => {
  return displayText.value.split('\n').filter((l, idx, arr) => idx < arr.length - 1 || l !== '')
})

const logContainer = ref(null)

watch(displayText, () => {
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
})
</script>

<style scoped>
.log-viewer { display: flex; flex-direction: column; }
.log-tabs { display: flex; gap: 4px; margin-bottom: 8px; }
.log-tabs button { padding: 4px 14px; border: 1px solid #ddd; border-radius: 6px; background: #f8f9fa; cursor: pointer; font-size: 12px; }
.log-tabs button.active { background: #3498db; color: #fff; border-color: #3498db; }
.log-content { background: #1e1e1e; color: #d4d4d4; border-radius: 8px; padding: 12px; max-height: 400px; overflow: auto; font-size: 12px; line-height: 1.6; }
.log-content pre { margin: 0; white-space: pre-wrap; word-break: break-all; }
.line-num { display: inline-block; width: 40px; color: #858585; user-select: none; }
</style>
