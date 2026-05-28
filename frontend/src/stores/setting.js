import { defineStore } from 'pinia'
import { settingApi } from '../api/setting'

export const useSettingStore = defineStore('setting', {
  state: () => ({
    settings: {},
    loading: false,
  }),
  actions: {
    async fetchAll() {
      this.loading = true
      try {
        const res = await settingApi.list()
        const map = {}
        for (const s of res.data) {
          map[s.key] = s.value
        }
        this.settings = map
      } finally {
        this.loading = false
      }
    },
    async update(key, value) {
      const res = await settingApi.update(key, value)
      this.settings[key] = res.data.value
    },
    get(key, defaultVal = '') {
      return this.settings[key] ?? defaultVal
    },
  },
})
