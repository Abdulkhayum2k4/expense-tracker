import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { authApi } from './api/client'
import { auth } from './stores/auth'
import './style.css'

// Confirm the cookie session (and refresh the cached profile) before the first
// route guard runs. A 401 just means "not logged in".
async function restoreSession() {
  try {
    auth.setUser(await authApi.me())
  } catch (e) {
    if (e.response?.status === 401) auth.clear()
    // Network errors keep the cached user; requests will retry later.
  }
}

restoreSession().finally(() => {
  createApp(App).use(router).mount('#app')
})
