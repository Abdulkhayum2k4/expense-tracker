<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { authApi, errorMessage } from '@/api/client'
import { auth } from '@/stores/auth'
import { theme } from '@/stores/theme'
import { toast } from '@/stores/toast'
import { CURRENCIES, localeFor } from '@/utils/currencies'

const router = useRouter()

// --- Profile & preferences ---
const profile = reactive({
  name: auth.state.user?.name ?? '',
  currency: auth.state.user?.currency ?? 'INR',
  budget_alerts: auth.state.user?.budget_alerts ?? true,
})
const preview = computed(() =>
  new Intl.NumberFormat(localeFor(profile.currency), { style: 'currency', currency: profile.currency }).format(123456.5),
)
const savingProfile = ref(false)
const profileError = ref('')

async function saveProfile() {
  profileError.value = ''
  savingProfile.value = true
  try {
    auth.setUser(await authApi.updateMe(profile))
    toast.show('Settings saved')
  } catch (e) {
    profileError.value = errorMessage(e)
  } finally {
    savingProfile.value = false
  }
}

const THEMES = [
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
  { value: 'system', label: 'System' },
]

// --- Password ---
const pw = reactive({ current: '', next: '', confirm: '' })
const pwError = ref('')
const savingPw = ref(false)

async function changePassword() {
  pwError.value = ''
  if (pw.next !== pw.confirm) {
    pwError.value = 'New passwords do not match.'
    return
  }
  savingPw.value = true
  try {
    const { user } = await authApi.changePassword(pw.current, pw.next)
    auth.setUser(user)
    Object.assign(pw, { current: '', next: '', confirm: '' })
    toast.show('Password changed. Other devices have been signed out.')
  } catch (e) {
    pwError.value = errorMessage(e)
  } finally {
    savingPw.value = false
  }
}

// --- Delete account ---
const deletePassword = ref('')
const deleteConfirm = ref('')
const deleteError = ref('')
const deleting = ref(false)

async function deleteAccount() {
  deleteError.value = ''
  deleting.value = true
  try {
    await authApi.deleteAccount(deletePassword.value)
    auth.clear()
    router.push({ name: 'register' })
  } catch (e) {
    deleteError.value = errorMessage(e)
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-2xl space-y-6">
    <div>
      <h1 class="text-2xl font-semibold">Settings</h1>
      <p class="text-sm text-slate-500">{{ auth.state.user?.email }}</p>
    </div>

    <!-- Profile & preferences -->
    <form class="card space-y-4" @submit.prevent="saveProfile">
      <h2 class="font-semibold">Profile & preferences</h2>
      <div>
        <label class="label" for="s-name">Name</label>
        <input id="s-name" v-model="profile.name" class="input" required maxlength="100" />
      </div>
      <div>
        <label class="label" for="s-currency">Currency</label>
        <select id="s-currency" v-model="profile.currency" class="input">
          <option v-for="c in CURRENCIES" :key="c.code" :value="c.code">{{ c.code }} · {{ c.label }}</option>
        </select>
        <p class="mt-1 text-xs text-slate-500">
          Changes how amounts are shown, e.g. {{ preview }}. Stored amounts are not converted.
        </p>
      </div>
      <label class="flex items-start gap-3">
        <input v-model="profile.budget_alerts" type="checkbox" class="mt-0.5 h-4 w-4 rounded border-slate-300 accent-indigo-600" />
        <span>
          <span class="block text-sm font-medium text-slate-700">Budget alerts</span>
          <span class="block text-xs text-slate-500">
            Show a notice when an expense takes a budget past 80% or over its limit.
          </span>
        </span>
      </label>
      <p v-if="profileError" class="alert-error">{{ profileError }}</p>
      <div class="flex justify-end">
        <button class="btn btn-primary" :disabled="savingProfile">{{ savingProfile ? 'Saving…' : 'Save' }}</button>
      </div>
    </form>

    <!-- Appearance (stored on this device) -->
    <section class="card">
      <h2 class="font-semibold">Appearance</h2>
      <p class="mb-3 text-xs text-slate-500">Saved on this device.</p>
      <div class="grid grid-cols-3 gap-2 rounded-lg bg-slate-100 p-1" role="radiogroup" aria-label="Theme">
        <button
          v-for="t in THEMES"
          :key="t.value"
          type="button"
          role="radio"
          :aria-checked="theme.preference.value === t.value"
          class="rounded-md py-1.5 text-sm font-medium transition"
          :class="theme.preference.value === t.value ? 'bg-surface text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'"
          @click="theme.set(t.value)"
        >
          {{ t.label }}
        </button>
      </div>
    </section>

    <!-- Password -->
    <form class="card space-y-4" @submit.prevent="changePassword">
      <h2 class="font-semibold">Change password</h2>
      <div>
        <label class="label" for="pw-current">Current password</label>
        <input id="pw-current" v-model="pw.current" type="password" class="input" autocomplete="current-password" required />
      </div>
      <div class="grid gap-4 sm:grid-cols-2">
        <div>
          <label class="label" for="pw-new">New password</label>
          <input
            id="pw-new"
            v-model="pw.next"
            type="password"
            class="input"
            autocomplete="new-password"
            minlength="8"
            maxlength="128"
            required
          />
        </div>
        <div>
          <label class="label" for="pw-confirm">Confirm new password</label>
          <input id="pw-confirm" v-model="pw.confirm" type="password" class="input" autocomplete="new-password" required />
        </div>
      </div>
      <p class="text-xs text-slate-500">Changing it signs you out on every other device.</p>
      <p v-if="pwError" class="alert-error">{{ pwError }}</p>
      <div class="flex justify-end">
        <button class="btn btn-primary" :disabled="savingPw">{{ savingPw ? 'Changing…' : 'Change password' }}</button>
      </div>
    </form>

    <!-- Danger zone -->
    <form class="card space-y-4 !border-red-300 dark:!border-red-900" @submit.prevent="deleteAccount">
      <div>
        <h2 class="font-semibold text-negative">Delete account</h2>
        <p class="text-sm text-slate-500">
          Permanently deletes your account and all of your transactions, categories, budgets and goals.
          This can't be undone.
        </p>
      </div>
      <div class="grid gap-4 sm:grid-cols-2">
        <div>
          <label class="label" for="del-pw">Password</label>
          <input id="del-pw" v-model="deletePassword" type="password" class="input" autocomplete="current-password" required />
        </div>
        <div>
          <label class="label" for="del-confirm">Type <strong>DELETE</strong> to confirm</label>
          <input id="del-confirm" v-model="deleteConfirm" class="input" autocomplete="off" required />
        </div>
      </div>
      <p v-if="deleteError" class="alert-error">{{ deleteError }}</p>
      <div class="flex justify-end">
        <button class="btn btn-danger" :disabled="deleting || deleteConfirm !== 'DELETE'">
          {{ deleting ? 'Deleting…' : 'Delete my account' }}
        </button>
      </div>
    </form>
  </div>
</template>
