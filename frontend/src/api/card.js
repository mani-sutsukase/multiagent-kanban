import client from './client'

export const cardApi = {
  list: (kanbanId, params) => client.get(`/kanbans/${kanbanId}/cards`, { params }),
  get: (id) => client.get(`/cards/${id}`),
  create: (kanbanId, data) => client.post(`/kanbans/${kanbanId}/cards`, data),
  update: (id, data) => client.put(`/cards/${id}`, data),
  delete: (id) => client.delete(`/cards/${id}`),
  reply: (id, reply) => client.post(`/cards/${id}/reply`, { reply }),
  advance: (id) => client.post(`/cards/${id}/advance`),
  clean: (id) => client.post(`/cards/${id}/clean`),
  move: (id, targetSwimlaneId) => client.post(`/cards/${id}/move`, { target_swimlane_id: targetSwimlaneId }),
  terminate: (id) => client.post(`/cards/${id}/terminate`),
}
