<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AuthLayout from '@/components/AuthLayout.vue'
import { authApi, errorMessage } from '@/api/client'
import { auth } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const form = reactive({ email: '', password: '' })
const loading = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  loading.value = true
  try {
    auth.setSession(await authApi.login(form))
    const redirect = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/')
      ? route.query.redirect
      : '/dashboard'
    router.push(redirect)
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AuthLayout title="Welcome back" subtitle="Log in to manage your money">
    <form class="space-y-4" @submit.prevent="submit">
      <div>
        <label class="label" for="email">Email</label>
        <input id="email" v-model="form.email" class="input" type="email" autocomplete="email" required />
      </div>
      <div>
        <label class="label" for="password">Password</label>
        <input id="password" v-model="form.password" class="input" type="password" autocomplete="current-password" required />
      </div>
      <p v-if="error" class="alert-error">{{ error }}</p>
      <button type="submit" class="btn btn-primary w-full" :disabled="loading">
        {{ loading ? 'Logging in…' : 'Log in' }}
      </button>
    </form>
    <template #footer>
      New here?
      <RouterLink to="/register" class="btn-link">Create an account</RouterLink>
    </template>
  </AuthLayout>
</template>
