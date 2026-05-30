import { defineStore } from 'pinia'
import { cardApi } from '../api/card'

export const useCardStore = defineStore('card', {
  state: () => ({
    cards: {},
    loading: false,
  }),
  actions: {
    async fetchByKanban(kanbanId, params = {}) {
      this.loading = true
      try {
        const res = await cardApi.list(kanbanId, params)
        this.cards[kanbanId] = res.data
        return res.data
      } finally {
        this.loading = false
      }
    },
    async create(kanbanId, data) {
      const res = await cardApi.create(kanbanId, data)
      if (this.cards[kanbanId]) {
        this.cards[kanbanId].push(res.data)
      }
      return res.data
    },
    async update(id, data) {
      const res = await cardApi.update(id, data)
      for (const kanbanId in this.cards) {
        const idx = this.cards[kanbanId].findIndex((c) => c.id === id)
        if (idx >= 0) {
          this.cards[kanbanId][idx] = res.data
        }
      }
      return res.data
    },
    async remove(id, kanbanId) {
      await cardApi.delete(id)
      if (this.cards[kanbanId]) {
        this.cards[kanbanId] = this.cards[kanbanId].filter((c) => c.id !== id)
      }
    },
    updateCardStatus(cardId, status, swimlaneId, result) {
      for (const kanbanId in this.cards) {
        const card = this.cards[kanbanId].find((c) => c.id === cardId)
        if (card) {
          card.status = status
          if (swimlaneId !== undefined) card.current_swimlane_id = swimlaneId
          if (result !== undefined) card.result = result
          break
        }
      }
    },
    async reply(cardId, replyText) {
      const res = await cardApi.reply(cardId, replyText)
      // 更新本地数据
      for (const kanbanId in this.cards) {
        const idx = this.cards[kanbanId].findIndex((c) => c.id === cardId)
        if (idx >= 0) {
          this.cards[kanbanId][idx] = res.data
        }
      }
      return res.data
    },
    async advance(cardId) {
      const res = await cardApi.advance(cardId)
      for (const kanbanId in this.cards) {
        const idx = this.cards[kanbanId].findIndex((c) => c.id === cardId)
        if (idx >= 0) {
          this.cards[kanbanId][idx] = res.data
        }
      }
      return res.data
    },
    async move(cardId, targetSwimlaneId) {
      const res = await cardApi.move(cardId, targetSwimlaneId)
      for (const kanbanId in this.cards) {
        const idx = this.cards[kanbanId].findIndex((c) => c.id === cardId)
        if (idx >= 0) {
          this.cards[kanbanId][idx] = res.data
        }
      }
      return res.data
    },
  },
})
