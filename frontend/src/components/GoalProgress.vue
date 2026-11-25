<script setup>
import { computed } from 'vue'
import { formatDate, formatMoney } from '@/utils/format'

/** A savings goal's progress bar and status. Status always has an icon + label, not colour alone. */
const props = defineProps({
  goal: { type: Object, required: true },
  compact: { type: Boolean, default: false },
})

const STATUS = {
  completed: { label: 'Reached', icon: '✓', color: '#0aac23', text: 'text-positive' },
  on_track: { label: 'On track', icon: '✓', color: '#0aac23', text: 'text-positive' },
  behind: { label: 'Behind', icon: '▲', color: '#fbb315', text: 'text-caution' },
  no_deadline: { label: 'No deadline', icon: '○', color: '#6a4ce2', text: 'text-slate-500' },
}
const status = computed(() => STATUS[props.goal.status])
const width = computed(() => `${Math.min(100, props.goal.percent)}%`)

const detail = computed(() => {
  const g = props.goal
  if (g.status === 'completed') return `${formatMoney(g.saved)} saved`
  if (g.monthly_needed == null) return `${formatMoney(g.remaining)} to go`
  if (g.months_left === 0) return `${formatMoney(g.remaining)} to go, deadline passed`
  return `${formatMoney(g.monthly_needed)}/month for ${g.months_left} ${g.months_left === 1 ? 'month' : 'months'}`
})
</script>

<template>
  <div>
    <div class="flex items-baseline justify-between gap-2 text-sm">
      <span class="truncate font-medium text-slate-900">{{ goal.name }}</span>
      <span class="shrink-0 tabular-nums text-slate-600">
        {{ formatMoney(goal.saved) }} <span class="text-slate-400">/ {{ formatMoney(goal.target_amount) }}</span>
      </span>
    </div>
    <div
      class="mt-1.5 h-2 overflow-hidden rounded-full bg-slate-100"
      role="progressbar"
      :aria-valuenow="Math.round(goal.percent)"
      aria-valuemin="0"
      aria-valuemax="100"
      :aria-label="`${goal.name} progress`"
    >
      <div class="h-full rounded-full transition-all" :style="{ width, backgroundColor: status.color }" />
    </div>
    <div class="mt-1 flex flex-wrap justify-between gap-x-3 text-xs">
      <span :class="status.text" class="font-medium">
        <span aria-hidden="true">{{ status.icon }}</span> {{ status.label }} · {{ goal.percent }}%
      </span>
      <span class="tabular-nums text-slate-500">
        {{ detail }}<template v-if="!compact && goal.target_date"> · by {{ formatDate(goal.target_date) }}</template>
      </span>
    </div>
  </div>
</template>
