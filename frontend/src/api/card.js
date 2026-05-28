import client from './client'

export const cardApi = {
  list: (kanbanId, params) => client.get(`/kanbans/${kanbanId}/cards`, { params }),
  get: (id) => client.get(`/cards/${id}`),
  create: (kanbanId, data) => client.post(`/kanbans/${kanbanId}/cards`, data),
  update: (id, data) => client.put(`/cards/${id}`, data),
  delete: (id) => client.delete(`/cards/${id}`),
}
