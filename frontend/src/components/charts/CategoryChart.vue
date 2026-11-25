<script setup>
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import { COLORS } from './chartSetup'
import { formatMoney, formatMoneyCompact } from '@/utils/format'

/** Horizontal bars, one per category. rows: [{ category, total }] sorted largest first. */
const props = defineProps({
  rows: { type: Array, required: true },
  type: { type: String, default: 'expense' },
})

const total = computed(() => props.rows.reduce((sum, r) => sum + r.total, 0))

const data = computed(() => ({
  labels: props.rows.map((r) => r.category),
  datasets: [
    {
      label: props.type === 'income' ? 'Income' : 'Spending',
      data: props.rows.map((r) => r.total),
      backgroundColor: COLORS[props.type],
      borderRadius: { topRight: 4, bottomRight: 4 },
      borderSkipped: 'left',
      maxBarThickness: 18,
    },
  ],
}))

const options = computed(() => ({
  indexAxis: 'y',
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx) => {
          const share = total.value ? ((ctx.parsed.x / total.value) * 100).toFixed(1) : 0
          return ` ${formatMoney(ctx.parsed.x)} (${share}%)`
        },
      },
    },
  },
  scales: {
    x: {
      beginAtZero: true,
      grid: { color: COLORS.grid },
      border: { display: false },
      ticks: { maxTicksLimit: 5, callback: (v) => formatMoneyCompact(v) },
    },
    y: { grid: { display: false }, border: { color: COLORS.axis }, ticks: { color: '#191919' } },
  },
}))

// Grow with the number of categories so bars never get squashed.
const height = computed(() => `${Math.max(160, props.rows.length * 34 + 40)}px`)
</script>

<template>
  <div :style="{ height }">
    <Bar :data="data" :options="options" :aria-label="`${type} by category bar chart`" role="img" />
  </div>
</template>
