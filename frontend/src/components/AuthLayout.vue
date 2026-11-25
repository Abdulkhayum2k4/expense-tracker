<script setup>
defineProps({ title: String, subtitle: String })
</script>

<template>
  <div class="flex min-h-screen items-center justify-center px-4 py-12">
    <div class="w-full max-w-sm">
      <div class="mb-8 text-center">
        <span class="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-xl bg-indigo-600 text-xl text-white">₹</span>
        <h1 class="text-2xl font-semibold">{{ title }}</h1>
        <p class="mt-1 text-sm text-slate-500">{{ subtitle }}</p>
      </div>
      <div class="card">
        <slot />
      </div>
      <p class="mt-6 text-center text-sm text-slate-500">
        <slot name="footer" />
      </p>
    </div>
  </div>
</template>
