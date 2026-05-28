import client from './client'

export const approvalApi = {
  listPending: () => client.get('/approvals/pending'),
  approve: (cardId, data) => client.post(`/cards/${cardId}/approve`, data),
  reject: (cardId, data) => client.post(`/cards/${cardId}/reject`, data),
}
