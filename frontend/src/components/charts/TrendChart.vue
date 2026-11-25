<script setup>
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import { COLORS } from './chartSetup'
import { MONTH_NAMES, formatMoney, formatMoneyCompact } from '@/utils/format'

/** points: [{ month: 1..12, income, expense }] */
const props = defineProps({ points: { type: Array, required: true } })

const data = computed(() => ({
  labels: props.points.map((p) => MONTH_NAMES[p.month - 1]),
  datasets: [
    { label: 'Income', data: props.points.map((p) => p.income), backgroundColor: COLORS.income },
    { label: 'Expense', data: props.points.map((p) => p.expense), backgroundColor: COLORS.expense },
  ].map((ds) => ({
    ...ds,
    borderRadius: { topLeft: 4, topRight: 4 },
    borderSkipped: 'bottom',
    borderColor: '#ffffff', // 2px surface gap between adjacent bars
    borderWidth: { left: 1, right: 1 },
    maxBarThickness: 16,
    categoryPercentage: 0.7,
    barPercentage: 0.9,
  })),
}))

const options = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: {
      position: 'top',
      align: 'end',
      labels: { usePointStyle: true, pointStyle: 'rectRounded', boxWidth: 10, boxHeight: 10 },
    },
    tooltip: {
      callbacks: { label: (ctx) => ` ${ctx.dataset.label}: ${formatMoney(ctx.parsed.y)}` },
    },
  },
  scales: {
    x: { grid: { display: false }, border: { color: COLORS.axis } },
    y: {
      beginAtZero: true,
      grid: { color: COLORS.grid },
      border: { display: false },
      ticks: { maxTicksLimit: 5, callback: (v) => formatMoneyCompact(v) },
    },
  },
}
</script>

<template>
  <div class="h-72">
    <Bar :data="data" :options="options" aria-label="Monthly income and expense bar chart" role="img" />
  </div>
</template>
