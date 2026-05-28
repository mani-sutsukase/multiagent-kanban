import { defineStore } from 'pinia'
import { kanbanApi } from '../api/kanban'

export const useKanbanStore = defineStore('kanban', {
  state: () => ({
    kanbans: [],
    currentKanban: null,
    loading: false,
  }),
  actions: {
    async fetchAll() {
      this.loading = true
      try {
        const res = await kanbanApi.list()
        this.kanbans = res.data
      } finally {
        this.loading = false
      }
    },
    async fetchOne(id) {
      this.loading = true
      try {
        const res = await kanbanApi.get(id)
        this.currentKanban = res.data
        return res.data
      } finally {
        this.loading = false
      }
    },
    async create(data) {
      const res = await kanbanApi.create(data)
      this.kanbans.push(res.data)
      return res.data
    },
    async update(id, data) {
      const res = await kanbanApi.update(id, data)
      const idx = this.kanbans.findIndex((k) => k.id === id)
      if (idx >= 0) this.kanbans[idx] = res.data
      if (this.currentKanban?.id === id) this.currentKanban = res.data
      return res.data
    },
    async remove(id) {
      await kanbanApi.delete(id)
      this.kanbans = this.kanbans.filter((k) => k.id !== id)
      if (this.currentKanban?.id === id) this.currentKanban = null
    },
    async addSwimlane(kanbanId, data) {
      const res = await kanbanApi.addSwimlane(kanbanId, data)
      if (this.currentKanban?.id === kanbanId) {
        await this.fetchOne(kanbanId)
      }
      return res.data
    },
    async updateSwimlane(id, data) {
      await kanbanApi.updateSwimlane(id, data)
      if (this.currentKanban) {
        await this.fetchOne(this.currentKanban.id)
      }
    },
    async deleteSwimlane(id) {
      await kanbanApi.deleteSwimlane(id)
      if (this.currentKanban) {
        await this.fetchOne(this.currentKanban.id)
      }
    },
    async reorderSwimlanes(kanbanId, swimlaneIds) {
      await kanbanApi.reorderSwimlanes(kanbanId, swimlaneIds)
      if (this.currentKanban?.id === kanbanId) {
        await this.fetchOne(kanbanId)
      }
    },
  },
})
