import axios from 'axios'
import { auth } from '@/stores/auth'
import router from '@/router'

const api = axios.create({
  baseURL: `${import.meta.env.VITE_API_URL || ''}/api`,
  timeout: 15000,
})

api.interceptors.request.use((config) => {
  if (auth.state.token) {
    config.headers.Authorization = `Bearer ${auth.state.token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    // An expired or invalid token: drop the session and send the user to log in again.
    if (error.response?.status === 401 && auth.state.token) {
      auth.logout()
      router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
    }
    return Promise.reject(error)
  },
)

/** Turn an axios error from FastAPI into one readable sentence. */
export function errorMessage(error, fallback = 'Something went wrong. Please try again.') {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((d) => {
        const field = d.loc?.filter((p) => p !== 'body').join('.')
        return field ? `${field}: ${d.msg}` : d.msg
      })
      .join('; ')
  }
  if (error?.code === 'ERR_NETWORK') return 'Cannot reach the server. Is the backend running?'
  return fallback
}

export const authApi = {
  register: (data) => api.post('/auth/register', data).then((r) => r.data),
  login: (data) => api.post('/auth/login', data).then((r) => r.data),
  me: () => api.get('/auth/me').then((r) => r.data),
}

export const categoriesApi = {
  list: (type) => api.get('/categories', { params: { type } }).then((r) => r.data),
  create: (data) => api.post('/categories', data).then((r) => r.data),
  update: (id, data) => api.put(`/categories/${id}`, data).then((r) => r.data),
  remove: (id) => api.delete(`/categories/${id}`),
}

export const transactionsApi = {
  list: (params) => api.get('/transactions', { params }).then((r) => r.data),
  create: (data) => api.post('/transactions', data).then((r) => r.data),
  update: (id, data) => api.put(`/transactions/${id}`, data).then((r) => r.data),
  remove: (id) => api.delete(`/transactions/${id}`),
}

export const budgetsApi = {
  list: (month, year) => api.get('/budgets', { params: { month, year } }).then((r) => r.data),
  create: (data) => api.post('/budgets', data).then((r) => r.data),
  update: (id, data) => api.put(`/budgets/${id}`, data).then((r) => r.data),
  remove: (id) => api.delete(`/budgets/${id}`),
}

export const analyticsApi = {
  summary: (month, year) => api.get('/analytics/summary', { params: { month, year } }).then((r) => r.data),
  trend: (year) => api.get('/analytics/trend', { params: { year } }).then((r) => r.data),
  /** month omitted = the whole year */
  breakdown: (year, month) => api.get('/analytics/breakdown', { params: { year, month } }).then((r) => r.data),
  compare: (month, year) => api.get('/analytics/compare', { params: { month, year } }).then((r) => r.data),
}

export default api
