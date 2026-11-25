<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import BudgetBar from '@/components/BudgetBar.vue'
import { budgetsApi, categoriesApi, errorMessage } from '@/api/client'
import { currentMonthValue, formatMoney, monthLabel, parseMonthValue } from '@/utils/format'

const monthValue = ref(currentMonthValue())
const selected = computed(() => parseMonthValue(monthValue.value))

const budgets = ref([])
const expenseCategories = ref([])
const loading = ref(true)
const error = ref('')

const form = reactive({ category: '', monthly_limit: '' })
const formError = ref('')
const saving = ref(false)

const editingId = ref(null)
const editLimit = ref('')

const unbudgeted = computed(() => {
  const used = new Set(budgets.value.map((b) => b.category))
  return expenseCategories.value.filter((c) => !used.has(c.name))
})
const totals = computed(() => ({
  limit: budgets.value.reduce((s, b) => s + b.monthly_limit, 0),
  spent: budgets.value.reduce((s, b) => s + b.spent, 0),
}))

watch(unbudgeted, (list) => {
  if (!list.some((c) => c.name === form.category)) form.category = list[0]?.name ?? ''
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    budgets.value = await budgetsApi.list(selected.value.month, selected.value.year)
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

async function addBudget() {
  formError.value = ''
  saving.value = true
  try {
    await budgetsApi.create({
      category: form.category,
      monthly_limit: Number(form.monthly_limit),
      ...selected.value,
    })
    form.monthly_limit = ''
    await load()
  } catch (e) {
    formError.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

function startEdit(b) {
  editingId.value = b.id
  editLimit.value = b.monthly_limit
}

async function saveEdit(b) {
  try {
    await budgetsApi.update(b.id, {
      category: b.category,
      monthly_limit: Number(editLimit.value),
      month: b.month,
      year: b.year,
    })
    editingId.value = null
    await load()
  } catch (e) {
    error.value = errorMessage(e)
  }
}

async function remove(b) {
  if (!confirm(`Remove the ${b.category} budget for ${monthLabel(b.month, b.year)}?`)) return
  try {
    await budgetsApi.remove(b.id)
    await load()
  } catch (e) {
    error.value = errorMessage(e)
  }
}

/** Copy last month's budgets into the selected month (skipping ones that already exist). */
async function copyFromPreviousMonth() {
  const { month, year } = selected.value
  const prev = month === 1 ? { month: 12, year: year - 1 } : { month: month - 1, year }
  error.value = ''
  try {
    const previous = await budgetsApi.list(prev.month, prev.year)
    const existing = new Set(budgets.value.map((b) => b.category))
    const toCopy = previous.filter((b) => !existing.has(b.category))
    if (!toCopy.length) {
      error.value = `Nothing to copy from ${monthLabel(prev.month, prev.year)}.`
      return
    }
    await Promise.all(
      toCopy.map((b) => budgetsApi.create({ category: b.category, monthly_limit: b.monthly_limit, month, year })),
    )
    await load()
  } catch (e) {
    error.value = errorMessage(e)
  }
}

watch(monthValue, (v) => v && load())
onMounted(async () => {
  load()
  try {
    expenseCategories.value = await categoriesApi.list('expense')
  } catch (e) {
    error.value = errorMessage(e)
  }
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-semibold">Budgets</h1>
        <p class="text-sm text-slate-500">Monthly spending limits per category.</p>
      </div>
      <input v-model="monthValue" type="month" class="input !w-auto" aria-label="Month" />
    </div>

    <p v-if="error" class="alert-error">{{ error }}</p>

    <div class="grid gap-6 lg:grid-cols-3">
      <section class="card lg:col-span-2">
        <div class="mb-4 flex flex-wrap items-center justify-between gap-2">
          <h2 class="font-semibold">{{ monthLabel(selected.month, selected.year) }}</h2>
          <p v-if="budgets.length" class="text-sm text-slate-500 tabular-nums">
            {{ formatMoney(totals.spent) }} of {{ formatMoney(totals.limit) }} spent
          </p>
        </div>

        <ul v-if="budgets.length" class="divide-y divide-slate-100">
          <li v-for="b in budgets" :key="b.id" class="py-4 first:pt-0 last:pb-0">
            <BudgetBar :budget="b" />
            <div class="mt-2 flex items-center justify-end gap-3">
              <template v-if="editingId === b.id">
                <input
                  v-model="editLimit"
                  type="number"
                  min="0.01"
                  step="0.01"
                  class="input !w-36 !py-1"
                  aria-label="New limit"
                  @keyup.enter="saveEdit(b)"
                />
                <button class="btn-link" @click="saveEdit(b)">Save</button>
                <button class="text-sm text-slate-500 hover:text-slate-700" @click="editingId = null">Cancel</button>
              </template>
              <template v-else>
                <button class="btn-link" @click="startEdit(b)">Edit limit</button>
                <button class="link-danger" @click="remove(b)">Remove</button>
              </template>
            </div>
          </li>
        </ul>
        <div v-else-if="!loading" class="py-10 text-center text-sm text-slate-500">
          <p>No budgets set for this month.</p>
          <button class="btn-link mt-2" @click="copyFromPreviousMonth">Copy last month's budgets</button>
        </div>
      </section>

      <section class="card h-fit">
        <h2 class="mb-4 font-semibold">Add a budget</h2>
        <form v-if="unbudgeted.length" class="space-y-4" @submit.prevent="addBudget">
          <div>
            <label class="label" for="b-category">Category</label>
            <select id="b-category" v-model="form.category" class="input" required>
              <option v-for="c in unbudgeted" :key="c.id" :value="c.name">{{ c.name }}</option>
            </select>
          </div>
          <div>
            <label class="label" for="b-limit">Monthly limit</label>
            <input id="b-limit" v-model="form.monthly_limit" type="number" min="0.01" step="0.01" class="input" required />
          </div>
          <p v-if="formError" class="alert-error">{{ formError }}</p>
          <button class="btn btn-primary w-full" :disabled="saving">{{ saving ? 'Adding…' : 'Add budget' }}</button>
        </form>
        <p v-else class="text-sm text-slate-500">Every expense category already has a budget this month.</p>
      </section>
    </div>
  </div>
</template>
