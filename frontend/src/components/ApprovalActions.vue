<template>
  <div class="approval-actions">
    <button class="btn btn-success" @click="approve" :disabled="loading">
      ✓ 批准
    </button>
    <button class="btn btn-danger" @click="showReject = true" :disabled="loading">
      ✗ 驳回
    </button>

    <RejectDialog
      v-if="showReject"
      @close="showReject = false"
      @confirm="reject"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useApprovalStore } from '../stores/approval'
import RejectDialog from './RejectDialog.vue'

const props = defineProps({
  cardId: String,
})

const emit = defineEmits(['approved', 'rejected'])
const approvalStore = useApprovalStore()
const loading = ref(false)
const showReject = ref(false)

async function approve() {
  loading.value = true
  try {
    await approvalStore.approveCard(props.cardId)
    emit('approved')
  } finally {
    loading.value = false
  }
}

async function reject(note) {
  loading.value = true
  try {
    await approvalStore.rejectCard(props.cardId, note)
    emit('rejected')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.approval-actions { display: flex; gap: 12px; justify-content: center; padding-top: 16px; border-top: 1px solid #eee; }
.btn { padding: 10px 32px; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; }
.btn:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-success { background: #27ae60; color: #fff; }
.btn-danger { background: #e74c3c; color: #fff; }
</style>
