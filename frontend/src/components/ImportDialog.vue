<script setup>
import { computed, reactive, ref, watch } from 'vue'
import Papa from 'papaparse'
import BaseModal from '@/components/BaseModal.vue'
import { errorMessage, transactionsApi } from '@/api/client'
import { AMOUNT_MODES, DATE_FORMATS, guessDateFormat, guessMapping, mapRows } from '@/utils/csvImport'
import { formatDate, formatMoney } from '@/utils/format'

const MAX_ROWS = 5000

const props = defineProps({ categories: { type: Array, required: true } })
const emit = defineEmits(['close', 'imported'])

const step = ref('file') // 'file' -> 'map' -> 'done'
const fileName = ref('')
const headers = ref([])
const rows = ref([])
const parseError = ref('')

const mapping = reactive(guessMapping([]))
const defaults = reactive({ expense: 'Other', income: 'Other' })
const createMissing = ref(true)

const importing = ref(false)
const importError = ref('')
const result = ref(null)

const expenseCategories = computed(() => props.categories.filter((c) => c.type === 'expense'))
const incomeCategories = computed(() => props.categories.filter((c) => c.type === 'income'))

function onFile(event) {
  const file = event.target.files?.[0]
  if (!file) return
  parseError.value = ''
  fileName.value = file.name
  Papa.parse(file, {
    header: true,
    skipEmptyLines: 'greedy',
    transformHeader: (h) => h.replace(/^﻿/, '').trim(),
    complete: ({ data, meta, errors }) => {
      if (!meta.fields?.length || !data.length) {
        parseError.value = errors[0]?.message || 'That file has no rows. Is it a CSV with a header row?'
        return
      }
      headers.value = meta.fields
      rows.value = data
      Object.assign(mapping, guessMapping(meta.fields))
      if (mapping.date) mapping.dateFormat = guessDateFormat(data.slice(0, 50).map((r) => r[mapping.date]))
      step.value = 'map'
    },
    error: (err) => (parseError.value = err.message),
  })
}

// Pick sensible default categories once the user's categories are known.
watch(
  () => props.categories,
  () => {
    for (const type of ['expense', 'income']) {
      const names = props.categories.filter((c) => c.type === type).map((c) => c.name)
      if (!names.includes(defaults[type])) defaults[type] = names.includes('Other') ? 'Other' : names[0] ?? 'Other'
    }
  },
  { immediate: true },
)

const mapped = computed(() => (step.value === 'map' ? mapRows(rows.value, mapping, defaults) : { valid: [], problems: [] }))
const preview = computed(() => mapped.value.valid.slice(0, 5))
const mappingComplete = computed(() => {
  if (!mapping.date || !mapping.title) return false
  if (mapping.amountMode === 'split') return Boolean(mapping.debit && mapping.credit)
  if (mapping.amountMode === 'type') return Boolean(mapping.amount && mapping.type)
  return Boolean(mapping.amount)
})

async function runImport() {
  importError.value = ''
  importing.value = true
  const { valid } = mapped.value
  try {
    const res = await transactionsApi.importRows(
      valid.map((v) => v.tx),
      createMissing.value,
    )
    // The API numbers rows by their position in what we sent; translate back to file lines.
    res.errors = res.errors.map((e) => ({ line: valid[e.row - 1]?.line ?? e.row, message: e.message }))
    result.value = res
    step.value = 'done'
    if (res.created) emit('imported', res)
  } catch (e) {
    importError.value = errorMessage(e)
  } finally {
    importing.value = false
  }
}

const FIELDS = computed(() => [
  { key: 'date', label: 'Date', required: true },
  { key: 'title', label: 'Title', required: true },
  { key: 'description', label: 'Description' },
  ...(mapping.amountMode === 'split'
    ? [
        { key: 'debit', label: 'Debit (money out)', required: true },
        { key: 'credit', label: 'Credit (money in)', required: true },
      ]
    : [{ key: 'amount', label: 'Amount', required: true }]),
  ...(mapping.amountMode === 'type' ? [{ key: 'type', label: 'Type column', required: true }] : []),
  { key: 'category', label: 'Category' },
])
</script>

<template>
  <BaseModal title="Import transactions from CSV" @close="emit('close')">
    <!-- Step 1: pick a file -->
    <div v-if="step === 'file'" class="space-y-4">
      <p class="text-sm text-slate-600">
        Upload a CSV from your bank or a spreadsheet. You'll match its columns in the next step,
        and nothing is saved until you confirm. Rows already in the app are skipped.
      </p>
      <label
        class="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-slate-300 px-4 py-10 text-center hover:border-indigo-400"
      >
        <span class="text-sm font-medium text-slate-700">Choose a .csv file</span>
        <span class="text-xs text-slate-500">Needs a header row. Up to {{ MAX_ROWS.toLocaleString() }} rows.</span>
        <input type="file" accept=".csv,text/csv" class="sr-only" @change="onFile" />
      </label>
      <p v-if="parseError" class="alert-error">{{ parseError }}</p>
    </div>

    <!-- Step 2: map columns, preview, confirm -->
    <div v-else-if="step === 'map'" class="max-h-[70vh] space-y-4 overflow-y-auto pr-1">
      <p class="text-sm text-slate-600">
        <strong>{{ fileName }}</strong> · {{ rows.length }} rows. Check how the columns are read.
      </p>

      <div>
        <label class="label" for="imp-mode">Amounts</label>
        <select id="imp-mode" v-model="mapping.amountMode" class="input">
          <option v-for="m in AMOUNT_MODES" :key="m.value" :value="m.value">{{ m.label }}</option>
        </select>
      </div>

      <div class="grid gap-3 sm:grid-cols-2">
        <div v-for="f in FIELDS" :key="f.key">
          <label class="label" :for="`imp-${f.key}`">
            {{ f.label }} <span v-if="!f.required" class="font-normal text-slate-400">(optional)</span>
          </label>
          <select :id="`imp-${f.key}`" v-model="mapping[f.key]" class="input">
            <option value="">{{ f.required ? 'Choose a column…' : 'None' }}</option>
            <option v-for="h in headers" :key="h" :value="h">{{ h }}</option>
          </select>
        </div>
        <div>
          <label class="label" for="imp-datefmt">Date format</label>
          <select id="imp-datefmt" v-model="mapping.dateFormat" class="input">
            <option v-for="d in DATE_FORMATS" :key="d.value" :value="d.value">{{ d.label }}</option>
          </select>
        </div>
      </div>

      <div class="grid gap-3 sm:grid-cols-2">
        <div>
          <label class="label" for="imp-def-exp">Category for expenses without one</label>
          <select id="imp-def-exp" v-model="defaults.expense" class="input">
            <option v-for="c in expenseCategories" :key="c.id" :value="c.name">{{ c.name }}</option>
          </select>
        </div>
        <div>
          <label class="label" for="imp-def-inc">Category for income without one</label>
          <select id="imp-def-inc" v-model="defaults.income" class="input">
            <option v-for="c in incomeCategories" :key="c.id" :value="c.name">{{ c.name }}</option>
          </select>
        </div>
      </div>

      <template v-if="mappingComplete">
        <div>
          <h3 class="mb-1 text-sm font-medium text-slate-700">Preview</h3>
          <div class="overflow-x-auto rounded-lg border border-slate-200">
            <table class="w-full text-xs">
              <thead class="bg-slate-50 text-left text-slate-500">
                <tr>
                  <th class="px-2 py-1.5 font-medium">Date</th>
                  <th class="px-2 py-1.5 font-medium">Title</th>
                  <th class="px-2 py-1.5 font-medium">Category</th>
                  <th class="px-2 py-1.5 text-right font-medium">Amount</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                <tr v-for="v in preview" :key="v.line">
                  <td class="whitespace-nowrap px-2 py-1.5">{{ formatDate(v.tx.date) }}</td>
                  <td class="max-w-[12rem] truncate px-2 py-1.5">{{ v.tx.title }}</td>
                  <td class="px-2 py-1.5">{{ v.tx.category }}</td>
                  <td class="whitespace-nowrap px-2 py-1.5 text-right tabular-nums" :class="v.tx.type === 'income' ? 'text-positive' : ''">
                    {{ v.tx.type === 'income' ? '+' : '−' }}{{ formatMoney(v.tx.amount) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="rounded-lg bg-slate-50 px-3 py-2 text-sm">
          <p>
            <span class="font-medium text-positive">✓ {{ mapped.valid.length }} ready to import</span>
            <template v-if="mapped.problems.length">
              · <span class="font-medium text-negative">! {{ mapped.problems.length }} can't be read</span>
            </template>
          </p>
          <ul v-if="mapped.problems.length" class="mt-1 max-h-28 overflow-y-auto text-xs text-slate-600">
            <li v-for="p in mapped.problems.slice(0, 50)" :key="p.line">Line {{ p.line }}: {{ p.message }}</li>
          </ul>
        </div>

        <label class="flex items-center gap-2 text-sm text-slate-700">
          <input v-model="createMissing" type="checkbox" class="h-4 w-4 accent-indigo-600" />
          Create categories from the file that don't exist yet
        </label>
      </template>
      <p v-else class="text-sm text-slate-500">Choose the required columns to see a preview.</p>

      <p v-if="mapped.valid.length > MAX_ROWS" class="alert-error">
        Too many rows ({{ mapped.valid.length }}). Split the file into parts of up to {{ MAX_ROWS }} rows.
      </p>
      <p v-if="importError" class="alert-error">{{ importError }}</p>

      <div class="flex justify-between gap-2 pt-1">
        <button type="button" class="btn btn-secondary" @click="step = 'file'">Back</button>
        <button
          type="button"
          class="btn btn-primary"
          :disabled="importing || !mappingComplete || !mapped.valid.length || mapped.valid.length > MAX_ROWS"
          @click="runImport"
        >
          {{ importing ? 'Importing…' : `Import ${mapped.valid.length} transactions` }}
        </button>
      </div>
    </div>

    <!-- Step 3: result -->
    <div v-else class="space-y-4 text-sm">
      <ul class="space-y-1">
        <li><span class="font-medium text-positive">✓ {{ result.created }}</span> transactions imported</li>
        <li v-if="result.skipped_duplicates">
          <span class="font-medium">{{ result.skipped_duplicates }}</span> skipped because they're already in the app
        </li>
        <li v-if="result.created_categories.length">
          New categories: {{ result.created_categories.join(', ') }}
        </li>
        <li v-if="result.errors.length" class="text-negative">! {{ result.errors.length }} rows rejected</li>
      </ul>
      <ul v-if="result.errors.length" class="max-h-32 overflow-y-auto text-xs text-slate-600">
        <li v-for="e in result.errors" :key="e.line">Line {{ e.line }}: {{ e.message }}</li>
      </ul>
      <div class="flex justify-end">
        <button class="btn btn-primary" @click="emit('close')">Done</button>
      </div>
    </div>
  </BaseModal>
</template>
