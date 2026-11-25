<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import AuthLayout from '@/components/AuthLayout.vue'
import { authApi, errorMessage } from '@/api/client'
import { auth } from '@/stores/auth'

const router = useRouter()
const form = reactive({ name: '', email: '', password: '', confirm: '' })
const loading = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  if (form.password !== form.confirm) {
    error.value = 'Passwords do not match.'
    return
  }
  loading.value = true
  try {
    const { name, email, password } = form
    auth.setSession(await authApi.register({ name, email, password }))
    router.push('/dashboard')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AuthLayout title="Create your account" subtitle="Start tracking where your money goes">
    <form class="space-y-4" @submit.prevent="submit">
      <div>
        <label class="label" for="name">Name</label>
        <input id="name" v-model="form.name" class="input" autocomplete="name" required maxlength="100" />
      </div>
      <div>
        <label class="label" for="email">Email</label>
        <input id="email" v-model="form.email" class="input" type="email" autocomplete="email" required />
      </div>
      <div>
        <label class="label" for="password">Password</label>
        <input
          id="password"
          v-model="form.password"
          class="input"
          type="password"
          autocomplete="new-password"
          minlength="8"
          maxlength="128"
          required
        />
        <p class="mt-1 text-xs text-slate-500">At least 8 characters.</p>
      </div>
      <div>
        <label class="label" for="confirm">Confirm password</label>
        <input id="confirm" v-model="form.confirm" class="input" type="password" autocomplete="new-password" required />
      </div>
      <p v-if="error" class="alert-error">{{ error }}</p>
      <button type="submit" class="btn btn-primary w-full" :disabled="loading">
        {{ loading ? 'Creating account…' : 'Create account' }}
      </button>
    </form>
    <template #footer>
      Already have an account?
      <RouterLink to="/login" class="btn-link">Log in</RouterLink>
    </template>
  </AuthLayout>
</template>
