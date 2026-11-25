<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { errorMessage, transactionsApi } from '@/api/client'
import { toast } from '@/stores/toast'
import { formatMoney, todayIso } from '@/utils/format'

const props = defineProps({
  /** Existing transaction to edit, or null to create one. */
  transaction: { type: Object, default: null },
  categories: { type: Array, required: true },
})
const emit = defineEmits(['saved', 'cancel'])

const form = reactive({
  title: props.transaction?.title ?? '',
  amount: props.transaction?.amount ?? '',
  type: props.transaction?.type ?? 'expense',
  category: props.transaction?.category ?? '',
  description: props.transaction?.description ?? '',
  date: props.transaction?.date ?? todayIso(),
})
const saving = ref(false)
const error = ref('')

const categoryOptions = computed(() => props.categories.filter((c) => c.type === form.type))

// When the type changes, the old category may not exist for the new type.
watch(
  categoryOptions,
  (options) => {
    if (!options.some((c) => c.name === form.category)) form.category = options[0]?.name ?? ''
  },
  { immediate: true },
)

/** The API sets budget_alert when this save pushed a budget past 80% or over 100%. */
function announceBudgetAlert(alert) {
  if (!alert) return
  const amounts = `${formatMoney(alert.spent)} of ${formatMoney(alert.monthly_limit)}`
  if (alert.level === 'exceeded') {
    toast.show(`${alert.category} is over budget: ${amounts} (${alert.percent_used}%)`, { kind: 'error', timeout: 8000 })
  } else {
    toast.show(`${alert.category} budget is at ${alert.percent_used}%: ${amounts}`, { kind: 'warning', timeout: 8000 })
  }
}

async function submit() {
  error.value = ''
  saving.value = true
  try {
    const payload = { ...form, amount: Number(form.amount) }
    const saved = props.transaction
      ? await transactionsApi.update(props.transaction.id, payload)
      : await transactionsApi.create(payload)
    toast.show(props.transaction ? 'Transaction updated' : 'Transaction added')
    announceBudgetAlert(saved.budget_alert)
    emit('saved', saved)
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <form class="space-y-4" @submit.prevent="submit">
    <div class="grid grid-cols-2 gap-2 rounded-lg bg-slate-100 p-1">
      <button
        v-for="t in ['expense', 'income']"
        :key="t"
        type="button"
        class="rounded-md py-1.5 text-sm font-medium capitalize transition"
        :class="form.type === t ? 'bg-surface text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'"
        @click="form.type = t"
      >
        {{ t }}
      </button>
    </div>

    <div>
      <label class="label" for="tx-title">Title</label>
      <input id="tx-title" v-model="form.title" class="input" required maxlength="100" placeholder="e.g. Lunch" />
    </div>

    <div class="grid grid-cols-2 gap-3">
      <div>
        <label class="label" for="tx-amount">Amount</label>
        <input id="tx-amount" v-model="form.amount" class="input" type="number" min="0.01" step="0.01" required />
      </div>
      <div>
        <label class="label" for="tx-date">Date</label>
        <input id="tx-date" v-model="form.date" class="input" type="date" required />
      </div>
    </div>

    <div>
      <label class="label" for="tx-category">Category</label>
      <select id="tx-category" v-model="form.category" class="input" required>
        <option v-for="c in categoryOptions" :key="c.id" :value="c.name">{{ c.name }}</option>
      </select>
      <p v-if="!categoryOptions.length" class="mt-1 text-xs text-slate-500">
        No {{ form.type }} categories yet. Add one on the Categories page.
      </p>
    </div>

    <div>
      <label class="label" for="tx-description">Description <span class="font-normal text-slate-400">(optional)</span></label>
      <textarea id="tx-description" v-model="form.description" class="input" rows="2" maxlength="500" />
    </div>

    <p v-if="error" class="alert-error">{{ error }}</p>

    <div class="flex justify-end gap-2 pt-1">
      <button type="button" class="btn btn-secondary" @click="emit('cancel')">Cancel</button>
      <button type="submit" class="btn btn-primary" :disabled="saving">
        {{ saving ? 'Saving…' : transaction ? 'Save changes' : 'Add transaction' }}
      </button>
    </div>
  </form>
</template>
