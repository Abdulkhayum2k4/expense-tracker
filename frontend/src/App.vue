<script setup>
import AppNav from '@/components/AppNav.vue'
import { auth } from '@/stores/auth'
</script>

<template>
  <div class="min-h-screen">
    <AppNav v-if="auth.isAuthenticated.value" />
    <main :class="auth.isAuthenticated.value ? 'mx-auto max-w-6xl px-4 py-6 sm:px-6' : ''">
      <RouterView />
    </main>
  </div>
</template>
