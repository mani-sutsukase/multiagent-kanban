import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const msg = error.response?.data?.detail || error.message || '网络错误'
    console.error('API Error:', msg)
    return Promise.reject(error)
  }
)

export default client
