<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import BaseModal from '@/components/BaseModal.vue'
import TransactionForm from '@/components/TransactionForm.vue'
import { categoriesApi, errorMessage, transactionsApi } from '@/api/client'
import { formatDate, formatMoney } from '@/utils/format'

const PAGE_SIZE = 15

const filters = reactive({ type: '', category: '', start_date: '', end_date: '', search: '' })
const page = ref(1)
const result = ref({ items: [], total: 0 })
const categories = ref([])
const loading = ref(true)
const error = ref('')

const editing = ref(null) // transaction being edited, or {} for a new one
const deleting = ref(null)
const deleteError = ref('')

const totalPages = computed(() => Math.max(1, Math.ceil(result.value.total / PAGE_SIZE)))
const filterCategories = computed(() =>
  categories.value.filter((c) => !filters.type || c.type === filters.type),
)
const uniqueCategoryNames = computed(() => [...new Set(filterCategories.value.map((c) => c.name))].sort())
const hasFilters = computed(() => Object.values(filters).some(Boolean))

async function load() {
  loading.value = true
  error.value = ''
  try {
    const params = { page: page.value, page_size: PAGE_SIZE }
    for (const [k, v] of Object.entries(filters)) if (v) params[k] = v
    result.value = await transactionsApi.list(params)
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

// Debounce so typing in the search box doesn't fire a request per keystroke.
let timer
watch(
  filters,
  () => {
    clearTimeout(timer)
    timer = setTimeout(() => {
      page.value = 1
      load()
    }, 300)
  },
  { deep: true },
)
watch(page, load)
watch(
  () => filters.type,
  () => {
    if (filters.category && !uniqueCategoryNames.value.includes(filters.category)) filters.category = ''
  },
)

function clearFilters() {
  Object.assign(filters, { type: '', category: '', start_date: '', end_date: '', search: '' })
}

function onSaved() {
  editing.value = null
  load()
}

async function confirmDelete() {
  deleteError.value = ''
  try {
    await transactionsApi.remove(deleting.value.id)
    deleting.value = null
    if (result.value.items.length === 1 && page.value > 1) page.value -= 1
    else load()
  } catch (e) {
    deleteError.value = errorMessage(e)
  }
}

onMounted(async () => {
  load()
  try {
    categories.value = await categoriesApi.list()
  } catch (e) {
    error.value = errorMessage(e)
  }
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <h1 class="text-2xl font-semibold">Transactions</h1>
      <button class="btn btn-primary" @click="editing = {}">+ Add transaction</button>
    </div>

    <!-- Filters -->
    <div class="card grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
      <div class="lg:col-span-2">
        <label class="label" for="f-search">Search</label>
        <input id="f-search" v-model="filters.search" class="input" placeholder="Title or description" />
      </div>
      <div>
        <label class="label" for="f-type">Type</label>
        <select id="f-type" v-model="filters.type" class="input">
          <option value="">All</option>
          <option value="expense">Expense</option>
          <option value="income">Income</option>
        </select>
      </div>
      <div>
        <label class="label" for="f-category">Category</label>
        <select id="f-category" v-model="filters.category" class="input">
          <option value="">All</option>
          <option v-for="name in uniqueCategoryNames" :key="name" :value="name">{{ name }}</option>
        </select>
      </div>
      <div>
        <label class="label" for="f-from">From</label>
        <input id="f-from" v-model="filters.start_date" type="date" class="input" />
      </div>
      <div>
        <label class="label" for="f-to">To</label>
        <input id="f-to" v-model="filters.end_date" type="date" class="input" />
      </div>
      <div v-if="hasFilters" class="sm:col-span-2 lg:col-span-6">
        <button class="btn-link" @click="clearFilters">Clear filters</button>
      </div>
    </div>

    <p v-if="error" class="alert-error">{{ error }}</p>

    <div class="card overflow-hidden !p-0">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th class="px-4 py-3 font-medium">Date</th>
              <th class="px-4 py-3 font-medium">Title</th>
              <th class="px-4 py-3 font-medium">Category</th>
              <th class="px-4 py-3 text-right font-medium">Amount</th>
              <th class="px-4 py-3"><span class="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="t in result.items" :key="t.id" class="hover:bg-slate-50">
              <td class="whitespace-nowrap px-4 py-3 text-slate-500">{{ formatDate(t.date) }}</td>
              <td class="px-4 py-3">
                <p class="font-medium">{{ t.title }}</p>
                <p v-if="t.description" class="max-w-xs truncate text-xs text-slate-500">{{ t.description }}</p>
              </td>
              <td class="whitespace-nowrap px-4 py-3">
                <span class="inline-flex items-center gap-1.5">
                  <span
                    class="h-2 w-2 rounded-sm"
                    :class="t.type === 'income' ? 'bg-income' : 'bg-expense'"
                    aria-hidden="true"
                  />
                  {{ t.category }}
                </span>
              </td>
              <td
                class="whitespace-nowrap px-4 py-3 text-right font-medium tabular-nums"
                :class="t.type === 'income' ? 'text-positive' : 'text-slate-900'"
              >
                {{ t.type === 'income' ? '+' : '−' }}{{ formatMoney(t.amount) }}
              </td>
              <td class="whitespace-nowrap px-4 py-3 text-right">
                <button class="btn-link mr-3" @click="editing = t">Edit</button>
                <button class="link-danger" @click="deleting = t">Delete</button>
              </td>
            </tr>
            <tr v-if="!loading && !result.items.length">
              <td colspan="5" class="px-4 py-12 text-center text-slate-500">
                {{ hasFilters ? 'No transactions match these filters.' : 'No transactions yet. Add your first one!' }}
              </td>
            </tr>
            <tr v-if="loading && !result.items.length">
              <td colspan="5" class="px-4 py-12 text-center text-slate-400">Loading…</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div
        v-if="result.total > PAGE_SIZE"
        class="flex items-center justify-between border-t border-slate-200 px-4 py-3 text-sm"
      >
        <span class="text-slate-500">{{ result.total }} transactions</span>
        <div class="flex items-center gap-2">
          <button class="btn btn-secondary !px-3 !py-1" :disabled="page <= 1" @click="page--">Previous</button>
          <span class="text-slate-600">Page {{ page }} of {{ totalPages }}</span>
          <button class="btn btn-secondary !px-3 !py-1" :disabled="page >= totalPages" @click="page++">Next</button>
        </div>
      </div>
    </div>

    <BaseModal
      v-if="editing"
      :title="editing.id ? 'Edit transaction' : 'Add transaction'"
      @close="editing = null"
    >
      <TransactionForm
        :transaction="editing.id ? editing : null"
        :categories="categories"
        @saved="onSaved"
        @cancel="editing = null"
      />
    </BaseModal>

    <BaseModal v-if="deleting" title="Delete transaction" @close="deleting = null; deleteError = ''">
      <p class="text-sm text-slate-600">
        Delete <strong>{{ deleting.title }}</strong> ({{ formatMoney(deleting.amount) }})? This can't be undone.
      </p>
      <p v-if="deleteError" class="alert-error mt-3">{{ deleteError }}</p>
      <div class="mt-5 flex justify-end gap-2">
        <button class="btn btn-secondary" @click="deleting = null; deleteError = ''">Cancel</button>
        <button class="btn btn-danger" @click="confirmDelete">Delete</button>
      </div>
    </BaseModal>
  </div>
</template>
