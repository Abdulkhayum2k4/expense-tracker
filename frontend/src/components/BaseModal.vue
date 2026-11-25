<script setup>
import { onBeforeUnmount, onMounted } from 'vue'

defineProps({ title: { type: String, required: true } })
const emit = defineEmits(['close'])

function onKey(e) {
  if (e.key === 'Escape') emit('close')
}
onMounted(() => document.addEventListener('keydown', onKey))
onBeforeUnmount(() => document.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/40 p-4 sm:items-center" @click.self="emit('close')">
      <div class="w-full max-w-lg rounded-xl bg-white shadow-xl" role="dialog" aria-modal="true" :aria-label="title">
        <div class="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <h2 class="text-lg font-semibold">{{ title }}</h2>
          <button class="rounded p-1 text-slate-400 hover:text-slate-600" aria-label="Close" @click="emit('close')">
            <svg class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>
        <div class="px-5 py-4">
          <slot />
        </div>
      </div>
    </div>
  </Teleport>
</template>
