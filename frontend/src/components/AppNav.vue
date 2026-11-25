<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { auth } from '@/stores/auth'
import { authApi } from '@/api/client'
import { theme } from '@/stores/theme'
import { currencySymbol } from '@/utils/format'

const links = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/transactions', label: 'Transactions' },
  { to: '/analytics', label: 'Analytics' },
  { to: '/budgets', label: 'Budgets' },
  { to: '/goals', label: 'Goals' },
  { to: '/categories', label: 'Categories' },
]

const router = useRouter()
const route = useRoute()
const menuOpen = ref(false)

watch(() => route.fullPath, () => (menuOpen.value = false))

// The quick toggle picks the opposite of what's showing; Settings also offers "System".
function toggleTheme() {
  theme.set(theme.isDark.value ? 'light' : 'dark')
}

async function logout() {
  try {
    await authApi.logout()
  } finally {
    auth.clear()
    router.push({ name: 'login' })
  }
}
</script>

<template>
  <header class="sticky top-0 z-30 border-b border-slate-200 bg-surface/90 backdrop-blur">
    <nav class="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
      <RouterLink to="/dashboard" class="flex items-center gap-2 font-semibold text-slate-900">
        <span class="grid h-8 w-8 place-items-center rounded-lg bg-indigo-600 text-sm text-white">{{ currencySymbol() }}</span>
        <span>Expense Tracker</span>
      </RouterLink>

      <div class="hidden items-center gap-1 lg:flex">
        <RouterLink
          v-for="link in links"
          :key="link.to"
          :to="link.to"
          class="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900"
          active-class="bg-indigo-50 !text-indigo-700 dark:bg-indigo-500/15 dark:!text-indigo-300"
        >
          {{ link.label }}
        </RouterLink>
      </div>

      <div class="hidden items-center gap-2 lg:flex">
        <button
          class="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-900"
          :aria-label="theme.isDark.value ? 'Switch to light mode' : 'Switch to dark mode'"
          :title="theme.isDark.value ? 'Light mode' : 'Dark mode'"
          @click="toggleTheme"
        >
          <svg v-if="theme.isDark.value" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="4" />
            <path stroke-linecap="round" d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
          </svg>
          <svg v-else class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linejoin="round" d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
          </svg>
        </button>
        <RouterLink
          to="/settings"
          class="rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 hover:text-slate-900"
          active-class="bg-indigo-50 !text-indigo-700 dark:bg-indigo-500/15 dark:!text-indigo-300"
          title="Settings"
        >
          {{ auth.state.user?.name }}
        </RouterLink>
        <button class="btn btn-secondary !px-3 !py-1.5" @click="logout">Log out</button>
      </div>

      <button
        class="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden"
        :aria-expanded="menuOpen"
        aria-label="Toggle menu"
        @click="menuOpen = !menuOpen"
      >
        <svg class="h-6 w-6" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path v-if="!menuOpen" stroke-linecap="round" d="M4 6h16M4 12h16M4 18h16" />
          <path v-else stroke-linecap="round" d="M6 6l12 12M18 6L6 18" />
        </svg>
      </button>
    </nav>

    <div v-if="menuOpen" class="border-t border-slate-200 px-4 py-3 lg:hidden">
      <RouterLink
        v-for="link in links"
        :key="link.to"
        :to="link.to"
        class="block rounded-lg px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
        active-class="bg-indigo-50 !text-indigo-700 dark:bg-indigo-500/15 dark:!text-indigo-300"
      >
        {{ link.label }}
      </RouterLink>
      <div class="mt-2 flex items-center justify-between border-t border-slate-200 px-3 pt-3">
        <RouterLink to="/settings" class="text-sm text-slate-600">{{ auth.state.user?.name }} · Settings</RouterLink>
        <div class="flex items-center gap-4">
          <button class="btn-link" @click="toggleTheme">{{ theme.isDark.value ? 'Light mode' : 'Dark mode' }}</button>
          <button class="btn-link" @click="logout">Log out</button>
        </div>
      </div>
    </div>
  </header>
</template>
