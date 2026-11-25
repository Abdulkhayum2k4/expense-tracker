<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { auth } from '@/stores/auth'

const links = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/transactions', label: 'Transactions' },
  { to: '/analytics', label: 'Analytics' },
  { to: '/budgets', label: 'Budgets' },
  { to: '/categories', label: 'Categories' },
]

const router = useRouter()
const route = useRoute()
const menuOpen = ref(false)

watch(() => route.fullPath, () => (menuOpen.value = false))

function logout() {
  auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <header class="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur">
    <nav class="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
      <RouterLink to="/dashboard" class="flex items-center gap-2 font-semibold text-slate-900">
        <span class="grid h-8 w-8 place-items-center rounded-lg bg-indigo-600 text-white">₹</span>
        <span>Expense Tracker</span>
      </RouterLink>

      <div class="hidden items-center gap-1 md:flex">
        <RouterLink
          v-for="link in links"
          :key="link.to"
          :to="link.to"
          class="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900"
          active-class="bg-indigo-50 !text-indigo-700"
        >
          {{ link.label }}
        </RouterLink>
      </div>

      <div class="hidden items-center gap-3 md:flex">
        <span class="text-sm text-slate-500">{{ auth.state.user?.name }}</span>
        <button class="btn btn-secondary !px-3 !py-1.5" @click="logout">Log out</button>
      </div>

      <button
        class="rounded-lg p-2 text-slate-600 hover:bg-slate-100 md:hidden"
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

    <div v-if="menuOpen" class="border-t border-slate-200 px-4 py-3 md:hidden">
      <RouterLink
        v-for="link in links"
        :key="link.to"
        :to="link.to"
        class="block rounded-lg px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
        active-class="bg-indigo-50 !text-indigo-700"
      >
        {{ link.label }}
      </RouterLink>
      <div class="mt-2 flex items-center justify-between border-t border-slate-200 px-3 pt-3">
        <span class="text-sm text-slate-500">{{ auth.state.user?.name }}</span>
        <button class="btn-link" @click="logout">Log out</button>
      </div>
    </div>
  </header>
</template>
