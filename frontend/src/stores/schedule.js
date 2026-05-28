import { defineStore } from 'pinia'
import { scheduleApi } from '../api/schedule'

export const useScheduleStore = defineStore('schedule', {
  state: () => ({
    schedules: [],
    loading: false,
  }),
  actions: {
    async fetchAll() {
      this.loading = true
      try {
        const res = await scheduleApi.list()
        this.schedules = res.data
      } finally {
        this.loading = false
      }
    },
    async create(data) {
      const res = await scheduleApi.create(data)
      this.schedules.push(res.data)
      return res.data
    },
    async update(id, data) {
      const res = await scheduleApi.update(id, data)
      const idx = this.schedules.findIndex((s) => s.id === id)
      if (idx >= 0) this.schedules[idx] = res.data
      return res.data
    },
    async remove(id) {
      await scheduleApi.delete(id)
      this.schedules = this.schedules.filter((s) => s.id !== id)
    },
    async toggle(id) {
      const res = await scheduleApi.toggle(id)
      const s = this.schedules.find((s) => s.id === id)
      if (s) s.enabled = res.data.enabled ? 1 : 0
      return res.data
    },
  },
})
