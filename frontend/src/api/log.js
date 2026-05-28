import client from './client'

export const logApi = {
  list: (cardId) => client.get(`/cards/${cardId}/logs`),
  getStdout: (logId) => client.get(`/logs/${logId}/stdout`),
  getStderr: (logId) => client.get(`/logs/${logId}/stderr`),
  cardSummary: (params) => client.get('/logs/cards/summary', { params }),
}
