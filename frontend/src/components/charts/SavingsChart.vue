<script setup>
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import { COLORS } from './chartSetup'
import { MONTH_NAMES, formatMoney, formatMoneyCompact } from '@/utils/format'

/** Net savings (income - expense) per month. points: [{ month, income, expense }] */
const props = defineProps({ points: { type: Array, required: true } })

const net = computed(() => props.points.map((p) => Math.round((p.income - p.expense) * 100) / 100))

const data = computed(() => ({
  labels: props.points.map((p) => MONTH_NAMES[p.month - 1]),
  datasets: [
    {
      label: 'Net savings',
      data: net.value,
      backgroundColor: net.value.map((v) => (v < 0 ? COLORS.deficit : COLORS.surplus)),
      borderRadius: 4,
      borderSkipped: 'start', // round only the end away from zero, for both signs
      maxBarThickness: 18,
    },
  ],
}))

const options = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx) => {
          const v = ctx.parsed.y
          return ` ${v < 0 ? 'Overspent' : 'Saved'}: ${formatMoney(Math.abs(v))}`
        },
      },
    },
  },
  scales: {
    x: { grid: { display: false }, border: { display: false } },
    y: {
      grid: {
        // Draw the zero line as the baseline, the others as hairlines.
        color: (ctx) => (ctx.tick.value === 0 ? COLORS.axis : COLORS.grid),
      },
      border: { display: false },
      ticks: { maxTicksLimit: 5, callback: (v) => formatMoneyCompact(v) },
    },
  },
}
</script>

<template>
  <div class="h-64">
    <Bar :data="data" :options="options" aria-label="Net savings per month bar chart" role="img" />
  </div>
</template>
