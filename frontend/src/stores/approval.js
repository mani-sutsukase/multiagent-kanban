import { defineStore } from 'pinia'
import { approvalApi } from '../api/approval'

export const useApprovalStore = defineStore('approval', {
  state: () => ({
    pendingList: [],
    loading: false,
  }),
  getters: {
    pendingCount: (state) => state.pendingList.length,
  },
  actions: {
    async fetchPending() {
      this.loading = true
      try {
        const res = await approvalApi.listPending()
        this.pendingList = res.data
      } finally {
        this.loading = false
      }
    },
    async approveCard(cardId, note = null) {
      const res = await approvalApi.approve(cardId, { note })
      this.pendingList = this.pendingList.filter((p) => p.card_id !== cardId)
      return res.data
    },
    async rejectCard(cardId, note) {
      const res = await approvalApi.reject(cardId, { note })
      this.pendingList = this.pendingList.filter((p) => p.card_id !== cardId)
      return res.data
    },
  },
})
