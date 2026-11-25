<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { categoriesApi, errorMessage } from '@/api/client'

const categories = ref([])
const error = ref('')
const form = reactive({ name: '', type: 'expense' })
const saving = ref(false)
const editingId = ref(null)
const editName = ref('')

const groups = computed(() => [
  { type: 'expense', title: 'Expense categories', dot: 'bg-expense', items: categories.value.filter((c) => c.type === 'expense') },
  { type: 'income', title: 'Income categories', dot: 'bg-income', items: categories.value.filter((c) => c.type === 'income') },
])

async function load() {
  try {
    categories.value = await categoriesApi.list()
  } catch (e) {
    error.value = errorMessage(e)
  }
}

async function add() {
  error.value = ''
  saving.value = true
  try {
    await categoriesApi.create(form)
    form.name = ''
    await load()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

function startEdit(c) {
  editingId.value = c.id
  editName.value = c.name
}

async function saveEdit(c) {
  error.value = ''
  try {
    await categoriesApi.update(c.id, { name: editName.value, type: c.type })
    editingId.value = null
    await load()
  } catch (e) {
    error.value = errorMessage(e)
  }
}

async function remove(c) {
  if (!confirm(`Delete the "${c.name}" category?`)) return
  error.value = ''
  try {
    await categoriesApi.remove(c.id)
    await load()
  } catch (e) {
    error.value = errorMessage(e)
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-2xl font-semibold">Categories</h1>
      <p class="text-sm text-slate-500">
        Renaming a category also updates its transactions and budgets. A category with transactions can't be deleted.
      </p>
    </div>

    <form class="card flex flex-wrap items-end gap-3" @submit.prevent="add">
      <div class="min-w-48 flex-1">
        <label class="label" for="c-name">New category</label>
        <input id="c-name" v-model="form.name" class="input" required maxlength="50" placeholder="e.g. Groceries" />
      </div>
      <div>
        <label class="label" for="c-type">Type</label>
        <select id="c-type" v-model="form.type" class="input">
          <option value="expense">Expense</option>
          <option value="income">Income</option>
        </select>
      </div>
      <button class="btn btn-primary" :disabled="saving">Add</button>
    </form>

    <p v-if="error" class="alert-error">{{ error }}</p>

    <div class="grid gap-6 md:grid-cols-2">
      <section v-for="g in groups" :key="g.type" class="card">
        <h2 class="mb-3 flex items-center gap-2 font-semibold">
          <span class="h-2.5 w-2.5 rounded-sm" :class="g.dot" aria-hidden="true" />
          {{ g.title }}
          <span class="text-sm font-normal text-slate-400">({{ g.items.length }})</span>
        </h2>
        <ul class="divide-y divide-slate-100">
          <li v-for="c in g.items" :key="c.id" class="flex items-center justify-between gap-3 py-2.5">
            <template v-if="editingId === c.id">
              <input
                v-model="editName"
                class="input !py-1"
                maxlength="50"
                aria-label="Category name"
                @keyup.enter="saveEdit(c)"
                @keyup.esc="editingId = null"
              />
              <div class="flex shrink-0 gap-3">
                <button class="btn-link" @click="saveEdit(c)">Save</button>
                <button class="text-sm text-slate-500 hover:text-slate-700" @click="editingId = null">Cancel</button>
              </div>
            </template>
            <template v-else>
              <span class="text-sm">{{ c.name }}</span>
              <div class="flex shrink-0 gap-3">
                <button class="btn-link" @click="startEdit(c)">Rename</button>
                <button class="link-danger" @click="remove(c)">Delete</button>
              </div>
            </template>
          </li>
          <li v-if="!g.items.length" class="py-6 text-center text-sm text-slate-500">None yet.</li>
        </ul>
      </section>
    </div>
  </div>
</template>
