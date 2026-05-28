<template>
  <div class="log-content-wrapper">
    <div class="log-tabs">
      <button :class="{ active: activeTab === 'stdout' }" @click="activeTab = 'stdout'">stdout</button>
      <button :class="{ active: activeTab === 'stderr' }" @click="activeTab = 'stderr'">stderr</button>
    </div>
    <div class="log-content" ref="scrollRef">
      <pre><template v-for="(line, idx) in displayLines" :key="idx"><span class="line-number">{{ idx + 1 }}</span><span class="line-text">{{ line }}</span><br /></template></pre>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps({
  text: { type: String, default: '' },
  textType: { type: String, default: 'stdout' },
})

const activeTab = ref(props.textType)
const scrollRef = ref(null)

const displayLines = computed(() => {
  return (activeTab.value === 'stdout' ? props.text : '').split('\n').filter(l => l !== undefined)
})

watch(displayLines, () => {
  nextTick(() => {
    if (scrollRef.value) {
      scrollRef.value.scrollTop = scrollRef.value.scrollHeight
    }
  })
})
</script>

<style scoped>
.log-content-wrapper { display: flex; flex-direction: column; }
.log-tabs { display: flex; gap: 4px; margin-bottom: 8px; }
.log-tabs button { padding: 4px 14px; border: 1px solid #ddd; border-radius: 6px; background: #f8f9fa; cursor: pointer; font-size: 12px; }
.log-tabs button.active { background: #3498db; color: #fff; border-color: #3498db; }
.log-content { background: #1e1e1e; color: #d4d4d4; border-radius: 8px; padding: 12px; max-height: 400px; overflow: auto; font-size: 12px; line-height: 1.6; }
.log-content pre { margin: 0; }
.line-number { display: inline-block; width: 40px; color: #858585; user-select: none; text-align: right; margin-right: 12px; }
.line-text { white-space: pre-wrap; word-break: break-all; }
</style>
