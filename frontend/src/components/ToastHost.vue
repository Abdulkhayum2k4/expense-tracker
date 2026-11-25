<script setup>
import { toast } from '@/stores/toast'

// Each kind has an icon and a label as well as a colour, so meaning never depends on colour alone.
const STYLES = {
  success: { icon: '✓', label: 'Done', bar: 'bg-[#0aac23]' },
  warning: { icon: '▲', label: 'Warning', bar: 'bg-[#fbb315]' },
  error: { icon: '!', label: 'Alert', bar: 'bg-[#dc3c3d]' },
}
</script>

<template>
  <div
    class="pointer-events-none fixed inset-x-0 bottom-4 z-[60] flex flex-col items-center gap-2 px-4 sm:inset-x-auto sm:right-4 sm:items-end"
    aria-live="polite"
  >
    <TransitionGroup
      enter-from-class="translate-y-2 opacity-0"
      enter-active-class="transition duration-200"
      leave-to-class="opacity-0"
      leave-active-class="transition duration-150"
    >
      <div
        v-for="t in toast.items"
        :key="t.id"
        class="pointer-events-auto flex w-full max-w-sm overflow-hidden rounded-lg border border-slate-200 bg-surface shadow-lg"
        role="status"
      >
        <div class="w-1.5 shrink-0" :class="STYLES[t.kind].bar" aria-hidden="true" />
        <div class="flex flex-1 items-start gap-2 px-3 py-2.5 text-sm">
          <span aria-hidden="true" class="font-semibold">{{ STYLES[t.kind].icon }}</span>
          <p class="flex-1 text-slate-800">
            <span class="sr-only">{{ STYLES[t.kind].label }}: </span>{{ t.message }}
          </p>
          <button class="text-slate-400 hover:text-slate-600" aria-label="Dismiss" @click="toast.dismiss(t.id)">✕</button>
        </div>
      </div>
    </TransitionGroup>
  </div>
</template>
