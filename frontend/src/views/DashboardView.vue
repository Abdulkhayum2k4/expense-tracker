<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import '@/components/charts/chartSetup'
import TrendChart from '@/components/charts/TrendChart.vue'
import CategoryChart from '@/components/charts/CategoryChart.vue'
import BudgetBar from '@/components/BudgetBar.vue'
import BaseModal from '@/components/BaseModal.vue'
import TransactionForm from '@/components/TransactionForm.vue'
import { analyticsApi, budgetsApi, categoriesApi, errorMessage } from '@/api/client'
import { auth } from '@/stores/auth'
import { currentMonthValue, formatDate, formatMoney, monthLabel, parseMonthValue } from '@/utils/format'

const monthValue = ref(currentMonthValue())
const selected = computed(() => parseMonthValue(monthValue.value))

const summary = ref(null)
const trend = ref(null)
const budgets = ref([])
const categories = ref([])
const loading = ref(true)
const error = ref('')
const showForm = ref(false)
const breakdownType = ref('expense')

const breakdownRows = computed(() =>
  summary.value ? summary.value[`${breakdownType.value}_by_category`] : [],
)
const breakdownTotal = computed(() => breakdownRows.value.reduce((s, r) => s + r.total, 0))
const hasTrendData = computed(() => trend.value?.points.some((p) => p.income || p.expense))

async function load() {
  loading.value = true
  error.value = ''
  const { month, year } = selected.value
  try {
    const [s, t, b] = await Promise.all([
      analyticsApi.summary(month, year),
      analyticsApi.trend(year),
      budgetsApi.list(month, year),
    ])
    summary.value = s
    trend.value = t
    budgets.value = b
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

async function openForm() {
  if (!categories.value.length) categories.value = await categoriesApi.list()
  showForm.value = true
}

function onSaved() {
  showForm.value = false
  load()
}

watch(monthValue, (v) => v && load())
onMounted(load)
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-semibold">Hi, {{ auth.state.user?.name?.split(' ')[0] }}</h1>
        <p class="text-sm text-slate-500">Here's your money for {{ monthLabel(selected.month, selected.year) }}.</p>
      </div>
      <div class="flex items-center gap-2">
        <input v-model="monthValue" type="month" class="input !w-auto" aria-label="Month" />
        <button class="btn btn-primary" @click="openForm">+ Add transaction</button>
      </div>
    </div>

    <p v-if="error" class="alert-error">{{ error }}</p>

    <!-- Totals -->
    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <div class="card bg-indigo-600 !border-indigo-600 text-white">
        <p class="text-sm text-indigo-100">Total balance</p>
        <p class="mt-2 text-2xl font-semibold">{{ summary ? formatMoney(summary.total_balance) : '—' }}</p>
        <p class="mt-1 text-xs text-indigo-100">All income minus all expenses, to end of {{ monthLabel(selected.month, selected.year) }}</p>
      </div>
      <div class="card">
        <p class="flex items-center gap-2 text-sm text-slate-500">
          <span class="h-2.5 w-2.5 rounded-sm bg-income" aria-hidden="true" /> Income
        </p>
        <p class="mt-2 text-2xl font-semibold">{{ summary ? formatMoney(summary.income) : '—' }}</p>
        <p class="mt-1 text-xs text-slate-500">this month</p>
      </div>
      <div class="card">
        <p class="flex items-center gap-2 text-sm text-slate-500">
          <span class="h-2.5 w-2.5 rounded-sm bg-expense" aria-hidden="true" /> Expenses
        </p>
        <p class="mt-2 text-2xl font-semibold">{{ summary ? formatMoney(summary.expense) : '—' }}</p>
        <p class="mt-1 text-xs text-slate-500">this month</p>
      </div>
      <div class="card">
        <p class="text-sm text-slate-500">Savings</p>
        <p class="mt-2 text-2xl font-semibold" :class="summary?.savings < 0 ? 'text-negative' : 'text-slate-900'">
          {{ summary ? formatMoney(summary.savings) : '—' }}
        </p>
        <p class="mt-1 text-xs text-slate-500">
          <template v-if="summary?.savings_rate != null">
            {{ summary.savings_rate < 0 ? 'Overspent by' : 'Saved' }} {{ Math.abs(summary.savings_rate) }}% of income
          </template>
          <template v-else>No income this month</template>
        </p>
      </div>
    </div>

    <div class="grid gap-6 lg:grid-cols-5">
      <!-- Category breakdown -->
      <section class="card lg:col-span-3">
        <div class="mb-4 flex items-center justify-between gap-2">
          <h2 class="font-semibold">By category</h2>
          <div class="flex rounded-lg bg-slate-100 p-0.5 text-sm">
            <button
              v-for="t in ['expense', 'income']"
              :key="t"
              class="rounded-md px-3 py-1 capitalize"
              :class="breakdownType === t ? 'bg-surface shadow-sm' : 'text-slate-500'"
              @click="breakdownType = t"
            >
              {{ t }}
            </button>
          </div>
        </div>
        <template v-if="breakdownRows.length">
          <CategoryChart :rows="breakdownRows" :type="breakdownType" />
          <!-- Table view of the same numbers -->
          <details class="mt-3 text-sm">
            <summary class="cursor-pointer text-slate-500 hover:text-slate-700">Show as table</summary>
            <table class="mt-2 w-full tabular-nums">
              <tbody>
                <tr v-for="r in breakdownRows" :key="r.category" class="border-t border-slate-100">
                  <td class="py-1.5">{{ r.category }}</td>
                  <td class="py-1.5 text-right">{{ formatMoney(r.total) }}</td>
                  <td class="w-16 py-1.5 text-right text-slate-500">
                    {{ ((r.total / breakdownTotal) * 100).toFixed(1) }}%
                  </td>
                </tr>
              </tbody>
            </table>
          </details>
        </template>
        <p v-else class="py-12 text-center text-sm text-slate-500">
          No {{ breakdownType }} recorded for this month.
        </p>
      </section>

      <!-- Budgets -->
      <section class="card lg:col-span-2">
        <div class="mb-4 flex items-center justify-between">
          <h2 class="font-semibold">Budgets</h2>
          <RouterLink to="/budgets" class="btn-link">Manage</RouterLink>
        </div>
        <div v-if="budgets.length" class="space-y-4">
          <BudgetBar v-for="b in budgets" :key="b.id" :budget="b" />
        </div>
        <p v-else class="py-12 text-center text-sm text-slate-500">
          No budgets for this month.
          <RouterLink to="/budgets" class="btn-link">Set one</RouterLink>
        </p>
      </section>
    </div>

    <!-- Year trend -->
    <section class="card">
      <div class="mb-2 flex items-center justify-between">
        <h2 class="font-semibold">Income vs expenses, {{ selected.year }}</h2>
        <RouterLink to="/analytics" class="btn-link">More analytics</RouterLink>
      </div>
      <TrendChart v-if="hasTrendData" :points="trend.points" />
      <p v-else class="py-12 text-center text-sm text-slate-500">No transactions in {{ selected.year }} yet.</p>
    </section>

    <!-- Recent -->
    <section class="card">
      <div class="mb-3 flex items-center justify-between">
        <h2 class="font-semibold">Recent transactions</h2>
        <RouterLink to="/transactions" class="btn-link">View all</RouterLink>
      </div>
      <ul v-if="summary?.recent_transactions.length" class="divide-y divide-slate-100">
        <li v-for="t in summary.recent_transactions" :key="t.id" class="flex items-center justify-between gap-4 py-3">
          <div class="min-w-0">
            <p class="truncate font-medium">{{ t.title }}</p>
            <p class="text-xs text-slate-500">{{ t.category }} · {{ formatDate(t.date) }}</p>
          </div>
          <span class="font-medium tabular-nums" :class="t.type === 'income' ? 'text-positive' : 'text-slate-900'">
            {{ t.type === 'income' ? '+' : '−' }}{{ formatMoney(t.amount) }}
          </span>
        </li>
      </ul>
      <p v-else class="py-8 text-center text-sm text-slate-500">No transactions this month.</p>
    </section>

    <BaseModal v-if="showForm" title="Add transaction" @close="showForm = false">
      <TransactionForm :categories="categories" @saved="onSaved" @cancel="showForm = false" />
    </BaseModal>
  </div>
</template>
