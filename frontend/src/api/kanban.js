import client from './client'

export const kanbanApi = {
  list: () => client.get('/kanbans'),
  get: (id) => client.get(`/kanbans/${id}`),
  create: (data) => client.post('/kanbans', data),
  update: (id, data) => client.put(`/kanbans/${id}`, data),
  delete: (id) => client.delete(`/kanbans/${id}`),
  addSwimlane: (kanbanId, data) => client.post(`/kanbans/${kanbanId}/swimlanes`, data),
  updateSwimlane: (id, data) => client.put(`/swimlanes/${id}`, data),
  deleteSwimlane: (id) => client.delete(`/swimlanes/${id}`),
  reorderSwimlanes: (kanbanId, swimlaneIds) =>
    client.put(`/kanbans/${kanbanId}/swimlanes/order`, { swimlane_ids: swimlaneIds }),
}
