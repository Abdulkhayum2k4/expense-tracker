<script setup>
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import { tooltipTheme, useChartColors } from './chartSetup'
import { MONTH_NAMES, formatMoney, formatMoneyCompact } from '@/utils/format'

/** Net savings (income - expense) per month. points: [{ month, income, expense }] */
const props = defineProps({ points: { type: Array, required: true } })
const colors = useChartColors()

const net = computed(() => props.points.map((p) => Math.round((p.income - p.expense) * 100) / 100))

const data = computed(() => ({
  labels: props.points.map((p) => MONTH_NAMES[p.month - 1]),
  datasets: [
    {
      label: 'Net savings',
      data: net.value,
      backgroundColor: net.value.map((v) => (v < 0 ? colors.value.deficit : colors.value.surplus)),
      borderRadius: 4,
      borderSkipped: 'start', // round only the end away from zero, for both signs
      maxBarThickness: 18,
    },
  ],
}))

const options = computed(() => {
  const c = colors.value
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        ...tooltipTheme(c),
        callbacks: {
          label: (ctx) => {
            const v = ctx.parsed.y
            return ` ${v < 0 ? 'Overspent' : 'Saved'}: ${formatMoney(Math.abs(v))}`
          },
        },
      },
    },
    scales: {
      x: { grid: { display: false }, border: { display: false }, ticks: { color: c.text } },
      y: {
        // Draw the zero line as the baseline, the others as hairlines.
        grid: { color: (ctx) => (ctx.tick.value === 0 ? c.axis : c.grid) },
        border: { display: false },
        ticks: { color: c.text, maxTicksLimit: 5, callback: (v) => formatMoneyCompact(v) },
      },
    },
  }
})
</script>

<template>
  <div class="h-64">
    <Bar :data="data" :options="options" aria-label="Net savings per month bar chart" role="img" />
  </div>
</template>
