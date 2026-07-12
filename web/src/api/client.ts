import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  headers: { 'Cache-Control': 'no-cache', 'Pragma': 'no-cache' },
})

client.interceptors.request.use((config) => {
  if (config.method === 'get' || !config.method) {
    config.params = { ...config.params, _t: Date.now() }
  }
  return config
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  },
)

export default client
