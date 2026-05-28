import client from './client'

export const scheduleApi = {
  list: () => client.get('/schedules'),
  create: (data) => client.post('/schedules', data),
  update: (id, data) => client.put(`/schedules/${id}`, data),
  delete: (id) => client.delete(`/schedules/${id}`),
  toggle: (id) => client.post(`/schedules/${id}/toggle`),
  logs: (id) => client.get(`/schedules/${id}/logs`),
}
