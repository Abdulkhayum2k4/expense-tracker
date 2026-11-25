<script setup>
import { computed } from 'vue'
import { formatMoney } from '@/utils/format'

/** A budget's progress. Status is shown with an icon + label, never colour alone. */
const props = defineProps({ budget: { type: Object, required: true } })

const status = computed(() => {
  const p = props.budget.percent_used
  if (p > 100) return { label: 'Over budget', icon: '!', color: '#dc3c3d', text: 'text-red-700' }
  if (p >= 80) return { label: 'Near limit', icon: '▲', color: '#fbb315', text: 'text-amber-700' }
  return { label: 'On track', icon: '✓', color: '#0aac23', text: 'text-green-700' }
})
const width = computed(() => `${Math.min(100, props.budget.percent_used)}%`)
</script>

<template>
  <div>
    <div class="flex items-baseline justify-between gap-2 text-sm">
      <span class="font-medium text-slate-900">{{ budget.category }}</span>
      <span class="text-slate-600 tabular-nums">
        {{ formatMoney(budget.spent) }} <span class="text-slate-400">/ {{ formatMoney(budget.monthly_limit) }}</span>
      </span>
    </div>
    <div
      class="mt-1.5 h-2 overflow-hidden rounded-full bg-slate-100"
      role="progressbar"
      :aria-valuenow="Math.round(budget.percent_used)"
      aria-valuemin="0"
      aria-valuemax="100"
      :aria-label="`${budget.category} budget used`"
    >
      <div class="h-full rounded-full transition-all" :style="{ width, backgroundColor: status.color }" />
    </div>
    <div class="mt-1 flex justify-between text-xs">
      <span :class="status.text" class="font-medium">
        <span aria-hidden="true">{{ status.icon }}</span> {{ status.label }} · {{ budget.percent_used }}%
      </span>
      <span class="text-slate-500 tabular-nums">
        {{ budget.remaining >= 0 ? `${formatMoney(budget.remaining)} left` : `${formatMoney(-budget.remaining)} over` }}
      </span>
    </div>
  </div>
</template>
