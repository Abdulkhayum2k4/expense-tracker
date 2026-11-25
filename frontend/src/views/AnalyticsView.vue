<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import '@/components/charts/chartSetup'
import TrendChart from '@/components/charts/TrendChart.vue'
import SavingsChart from '@/components/charts/SavingsChart.vue'
import CategoryChart from '@/components/charts/CategoryChart.vue'
import { analyticsApi, errorMessage } from '@/api/client'
import { MONTH_NAMES, formatMoney, monthLabel } from '@/utils/format'

const now = new Date()
const year = ref(now.getFullYear())
const period = ref(now.getMonth() + 1) // 0 = whole year, 1..12 = a month
const breakdownType = ref('expense')

const trend = ref(null)
const breakdown = ref(null)
const comparison = ref(null)
const error = ref('')

const years = computed(() => Array.from({ length: 6 }, (_, i) => now.getFullYear() - i))
const periodLabel = computed(() => (period.value ? monthLabel(period.value, year.value) : `${year.value}`))

// Year totals and averages, from the monthly trend.
const yearStats = computed(() => {
  if (!trend.value) return null
  const pts = trend.value.points
  const income = pts.reduce((s, p) => s + p.income, 0)
  const expense = pts.reduce((s, p) => s + p.expense, 0)
  const active = pts.filter((p) => p.income || p.expense)
  const months = active.length || 1
  const top = [...pts].sort((a, b) => b.expense - a.expense)[0]
  return {
    income,
    expense,
    savings: income - expense,
    savingsRate: income ? ((income - expense) / income) * 100 : null,
    avgSpending: expense / months,
    topMonth: top?.expense ? top : null,
    hasData: active.length > 0,
  }
})

const breakdownRows = computed(() => breakdown.value?.[`${breakdownType.value}_by_category`] ?? [])
const breakdownTotal = computed(() => breakdownRows.value.reduce((s, r) => s + r.total, 0))

async function loadYear() {
  try {
    trend.value = await analyticsApi.trend(year.value)
  } catch (e) {
    error.value = errorMessage(e)
  }
}

async function loadPeriod() {
  try {
    const month = period.value || undefined
    const [b, c] = await Promise.all([
      analyticsApi.breakdown(year.value, month),
      month ? analyticsApi.compare(month, year.value) : Promise.resolve(null),
    ])
    breakdown.value = b
    comparison.value = c
  } catch (e) {
    error.value = errorMessage(e)
  }
}

function load() {
  error.value = ''
  loadYear()
  loadPeriod()
}

watch(year, load)
watch(period, () => {
  error.value = ''
  loadPeriod()
})
onMounted(load)

function changeLabel(row) {
  if (row.change === 0) return 'No change'
  if (row.change_pct === null) return 'New'
  return `${row.change > 0 ? '+' : ''}${row.change_pct}%`
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-semibold">Analytics</h1>
        <p class="text-sm text-slate-500">Monthly spending, category breakdown and trends.</p>
      </div>
      <div class="flex items-center gap-2">
        <select v-model="period" class="input !w-auto" aria-label="Period">
          <option :value="0">Whole year</option>
          <option v-for="(name, i) in MONTH_NAMES" :key="i" :value="i + 1">{{ name }}</option>
        </select>
        <select v-model="year" class="input !w-auto" aria-label="Year">
          <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
        </select>
      </div>
    </div>

    <p v-if="error" class="alert-error">{{ error }}</p>

    <!-- Year at a glance -->
    <div v-if="yearStats" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <div class="card">
        <p class="text-sm text-slate-500">Spent in {{ year }}</p>
        <p class="mt-2 text-2xl font-semibold">{{ formatMoney(yearStats.expense) }}</p>
        <p class="mt-1 text-xs text-slate-500">of {{ formatMoney(yearStats.income) }} earned</p>
      </div>
      <div class="card">
        <p class="text-sm text-slate-500">Saved in {{ year }}</p>
        <p class="mt-2 text-2xl font-semibold" :class="yearStats.savings < 0 ? 'text-red-700' : ''">
          {{ formatMoney(yearStats.savings) }}
        </p>
        <p class="mt-1 text-xs text-slate-500">
          {{ yearStats.savingsRate === null ? 'No income recorded' : `${yearStats.savingsRate.toFixed(1)}% of income` }}
        </p>
      </div>
      <div class="card">
        <p class="text-sm text-slate-500">Average monthly spending</p>
        <p class="mt-2 text-2xl font-semibold">{{ formatMoney(yearStats.avgSpending) }}</p>
        <p class="mt-1 text-xs text-slate-500">over months with activity</p>
      </div>
      <div class="card">
        <p class="text-sm text-slate-500">Highest-spending month</p>
        <p class="mt-2 text-2xl font-semibold">
          {{ yearStats.topMonth ? monthLabel(yearStats.topMonth.month, year) : '—' }}
        </p>
        <p class="mt-1 text-xs text-slate-500">
          {{ yearStats.topMonth ? formatMoney(yearStats.topMonth.expense) : 'No spending yet' }}
        </p>
      </div>
    </div>

    <!-- Trends -->
    <div class="grid gap-6 lg:grid-cols-2">
      <section class="card">
        <h2 class="mb-2 font-semibold">Monthly income vs spending</h2>
        <TrendChart v-if="yearStats?.hasData" :points="trend.points" />
        <p v-else class="py-16 text-center text-sm text-slate-500">No transactions in {{ year }}.</p>
      </section>
      <section class="card">
        <h2 class="font-semibold">Net savings per month</h2>
        <p class="mb-2 text-xs text-slate-500">Above zero: saved. Below zero: spent more than earned.</p>
        <SavingsChart v-if="yearStats?.hasData" :points="trend.points" />
        <p v-else class="py-16 text-center text-sm text-slate-500">No transactions in {{ year }}.</p>
      </section>
    </div>

    <div class="grid gap-6 lg:grid-cols-5">
      <!-- Category breakdown for the period -->
      <section class="card lg:col-span-3">
        <div class="mb-4 flex flex-wrap items-center justify-between gap-2">
          <h2 class="font-semibold">Category breakdown · {{ periodLabel }}</h2>
          <div class="flex rounded-lg bg-slate-100 p-0.5 text-sm">
            <button
              v-for="t in ['expense', 'income']"
              :key="t"
              class="rounded-md px-3 py-1 capitalize"
              :class="breakdownType === t ? 'bg-white shadow-sm' : 'text-slate-500'"
              @click="breakdownType = t"
            >
              {{ t }}
            </button>
          </div>
        </div>
        <template v-if="breakdownRows.length">
          <CategoryChart :rows="breakdownRows" :type="breakdownType" />
          <table class="mt-4 w-full text-sm tabular-nums">
            <thead class="text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th class="py-1.5 font-medium">Category</th>
                <th class="py-1.5 text-right font-medium">Amount</th>
                <th class="w-20 py-1.5 text-right font-medium">Share</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in breakdownRows" :key="r.category" class="border-t border-slate-100">
                <td class="py-1.5">{{ r.category }}</td>
                <td class="py-1.5 text-right">{{ formatMoney(r.total) }}</td>
                <td class="py-1.5 text-right text-slate-500">{{ ((r.total / breakdownTotal) * 100).toFixed(1) }}%</td>
              </tr>
              <tr class="border-t border-slate-200 font-medium">
                <td class="py-1.5">Total</td>
                <td class="py-1.5 text-right">{{ formatMoney(breakdownTotal) }}</td>
                <td />
              </tr>
            </tbody>
          </table>
        </template>
        <p v-else class="py-16 text-center text-sm text-slate-500">No {{ breakdownType }} in {{ periodLabel }}.</p>
      </section>

      <!-- Month-over-month -->
      <section class="card lg:col-span-2">
        <template v-if="comparison">
          <h2 class="font-semibold">Spending vs last month</h2>
          <p class="mb-4 text-xs text-slate-500">
            {{ monthLabel(comparison.month, comparison.year) }} compared with
            {{ monthLabel(comparison.previous_month, comparison.previous_year) }}
          </p>
          <div class="mb-4 flex items-baseline justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm">
            <span class="text-slate-600">Total</span>
            <span class="tabular-nums">
              <span class="font-semibold">{{ formatMoney(comparison.current_total) }}</span>
              <span class="text-slate-400"> vs {{ formatMoney(comparison.previous_total) }}</span>
            </span>
          </div>
          <ul v-if="comparison.categories.length" class="divide-y divide-slate-100 text-sm">
            <li v-for="r in comparison.categories" :key="r.category" class="flex items-center justify-between gap-3 py-2">
              <div class="min-w-0">
                <p class="truncate font-medium">{{ r.category }}</p>
                <p class="text-xs text-slate-500 tabular-nums">
                  {{ formatMoney(r.current) }} <span class="text-slate-400">vs {{ formatMoney(r.previous) }}</span>
                </p>
              </div>
              <!-- More spending is shown as bad (red), less as good (green); the arrow carries it too. -->
              <span
                class="shrink-0 rounded-full px-2 py-0.5 text-xs font-medium tabular-nums"
                :class="r.change > 0 ? 'bg-red-50 text-red-700' : r.change < 0 ? 'bg-green-50 text-green-700' : 'bg-slate-100 text-slate-600'"
              >
                <span aria-hidden="true">{{ r.change > 0 ? '▲' : r.change < 0 ? '▼' : '' }}</span>
                {{ changeLabel(r) }}
              </span>
            </li>
          </ul>
          <p v-else class="py-10 text-center text-sm text-slate-500">No spending in either month.</p>
        </template>
        <div v-else class="py-16 text-center text-sm text-slate-500">
          Pick a single month to compare it with the month before.
        </div>
      </section>
    </div>
  </div>
</template>
