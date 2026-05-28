import client from './client'

export const settingApi = {
  list: () => client.get('/settings'),
  get: (key) => client.get(`/settings/${key}`),
  update: (key, value) => client.put(`/settings/${key}`, { value }),
}
