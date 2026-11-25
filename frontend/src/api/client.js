import axios from 'axios'
import { auth } from '@/stores/auth'
import router from '@/router'

export const API_BASE = `${import.meta.env.VITE_API_URL || ''}/api`

const api = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
  withCredentials: true, // send the httpOnly auth cookie
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    // The session expired or was revoked: forget the user and send them to log in again.
    const isLoginAttempt = error.config?.url?.startsWith('/auth/login')
    if (error.response?.status === 401 && auth.state.user && !isLoginAttempt) {
      auth.clear()
      router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
    }
    if (error.response?.status === 429) {
      error.response.data = { detail: 'Too many attempts. Please wait a minute and try again.' }
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
  logout: () => api.post('/auth/logout'),
  changePassword: (current_password, new_password) =>
    api.put('/auth/password', { current_password, new_password }).then((r) => r.data),
  deleteAccount: (password) => api.delete('/auth/me', { data: { password } }),
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
