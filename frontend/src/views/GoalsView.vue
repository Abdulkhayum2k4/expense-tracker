<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import BaseModal from '@/components/BaseModal.vue'
import GoalProgress from '@/components/GoalProgress.vue'
import { errorMessage, goalsApi } from '@/api/client'
import { toast } from '@/stores/toast'
import { formatDate, formatMoney, todayIso } from '@/utils/format'

const goals = ref([])
const loading = ref(true)
const error = ref('')

const totals = computed(() => ({
  saved: goals.value.reduce((s, g) => s + g.saved, 0),
  target: goals.value.reduce((s, g) => s + g.target_amount, 0),
}))

async function load() {
  error.value = ''
  try {
    goals.value = await goalsApi.list()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

function replace(updated) {
  const i = goals.value.findIndex((g) => g.id === updated.id)
  if (i === -1) goals.value.push(updated)
  else goals.value[i] = updated
}

// --- Create / edit goal ---
const editing = ref(null) // {} for new, goal for edit
const goalForm = reactive({ name: '', target_amount: '', target_date: '' })
const goalError = ref('')
const savingGoal = ref(false)

function openGoal(goal) {
  editing.value = goal ?? {}
  goalError.value = ''
  Object.assign(goalForm, {
    name: goal?.name ?? '',
    target_amount: goal?.target_amount ?? '',
    target_date: goal?.target_date ?? '',
  })
}

async function saveGoal() {
  goalError.value = ''
  savingGoal.value = true
  const payload = {
    name: goalForm.name,
    target_amount: Number(goalForm.target_amount),
    target_date: goalForm.target_date || null,
  }
  try {
    const saved = editing.value.id
      ? await goalsApi.update(editing.value.id, payload)
      : await goalsApi.create(payload)
    editing.value = null
    toast.show(`Goal "${saved.name}" saved`)
    await load() // re-sort
  } catch (e) {
    goalError.value = errorMessage(e)
  } finally {
    savingGoal.value = false
  }
}

async function deleteGoal(goal) {
  if (!confirm(`Delete the goal "${goal.name}" and its history?`)) return
  try {
    await goalsApi.remove(goal.id)
    goals.value = goals.value.filter((g) => g.id !== goal.id)
  } catch (e) {
    error.value = errorMessage(e)
  }
}

// --- Add / withdraw money ---
const moving = ref(null) // { goal, direction: 'add' | 'withdraw' }
const moneyForm = reactive({ amount: '', date: todayIso(), note: '' })
const moneyError = ref('')
const savingMoney = ref(false)

function openMoney(goal, direction) {
  moving.value = { goal, direction }
  moneyError.value = ''
  Object.assign(moneyForm, { amount: '', date: todayIso(), note: '' })
}

async function saveMoney() {
  moneyError.value = ''
  savingMoney.value = true
  const { goal, direction } = moving.value
  const amount = Math.abs(Number(moneyForm.amount)) * (direction === 'withdraw' ? -1 : 1)
  try {
    const updated = await goalsApi.contribute(goal.id, { amount, date: moneyForm.date, note: moneyForm.note })
    replace(updated)
    moving.value = null
    if (goal.status !== 'completed' && updated.status === 'completed') {
      toast.show(`🎉 You reached your "${updated.name}" goal!`, { timeout: 6000 })
    }
  } catch (e) {
    moneyError.value = errorMessage(e)
  } finally {
    savingMoney.value = false
  }
}

// --- History ---
const expanded = ref(new Set())
function toggleHistory(id) {
  const next = new Set(expanded.value)
  next.has(id) ? next.delete(id) : next.add(id)
  expanded.value = next
}

async function removeContribution(goal, c) {
  try {
    replace(await goalsApi.removeContribution(goal.id, c.id))
  } catch (e) {
    error.value = errorMessage(e)
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-semibold">Savings goals</h1>
        <p class="text-sm text-slate-500">
          Money you set aside for a goal is tracked here; it doesn't change your income, expenses or balance.
        </p>
      </div>
      <button class="btn btn-primary" @click="openGoal()">+ New goal</button>
    </div>

    <p v-if="error" class="alert-error">{{ error }}</p>

    <div v-if="goals.length" class="card flex flex-wrap items-baseline justify-between gap-2">
      <span class="text-sm text-slate-500">Saved across {{ goals.length }} {{ goals.length === 1 ? 'goal' : 'goals' }}</span>
      <span class="tabular-nums">
        <span class="text-xl font-semibold">{{ formatMoney(totals.saved) }}</span>
        <span class="text-slate-400"> of {{ formatMoney(totals.target) }}</span>
      </span>
    </div>

    <div v-if="goals.length" class="grid gap-4 md:grid-cols-2">
      <section v-for="g in goals" :key="g.id" class="card space-y-4">
        <GoalProgress :goal="g" />
        <div class="flex flex-wrap items-center gap-2">
          <button class="btn btn-primary !px-3 !py-1.5" @click="openMoney(g, 'add')">Add money</button>
          <button class="btn btn-secondary !px-3 !py-1.5" :disabled="g.saved <= 0" @click="openMoney(g, 'withdraw')">
            Withdraw
          </button>
          <span class="flex-1" />
          <button class="btn-link" @click="openGoal(g)">Edit</button>
          <button class="link-danger" @click="deleteGoal(g)">Delete</button>
        </div>
        <div v-if="g.contributions.length" class="border-t border-slate-100 pt-3">
          <button class="text-xs text-slate-500 hover:text-slate-700" @click="toggleHistory(g.id)">
            {{ expanded.has(g.id) ? '▾ Hide history' : `▸ History (${g.contributions.length})` }}
          </button>
          <ul v-if="expanded.has(g.id)" class="mt-2 divide-y divide-slate-100 text-sm">
            <li v-for="c in g.contributions" :key="c.id" class="flex items-center justify-between gap-3 py-1.5">
              <span class="min-w-0">
                <span class="text-slate-500">{{ formatDate(c.date) }}</span>
                <span v-if="c.note" class="ml-2 truncate">{{ c.note }}</span>
              </span>
              <span class="flex shrink-0 items-center gap-3">
                <span class="tabular-nums" :class="c.amount < 0 ? 'text-negative' : 'text-positive'">
                  {{ c.amount < 0 ? '−' : '+' }}{{ formatMoney(Math.abs(c.amount)) }}
                </span>
                <button class="text-xs text-slate-400 hover:text-red-600" :aria-label="`Remove entry from ${c.date}`" @click="removeContribution(g, c)">
                  ✕
                </button>
              </span>
            </li>
          </ul>
        </div>
      </section>
    </div>

    <div v-else-if="!loading" class="card py-16 text-center">
      <p class="text-slate-600">No goals yet.</p>
      <p class="mt-1 text-sm text-slate-500">Saving for a laptop, a trip or an emergency fund? Set a target and track it here.</p>
      <button class="btn btn-primary mt-4" @click="openGoal()">Create your first goal</button>
    </div>

    <!-- Create / edit -->
    <BaseModal v-if="editing" :title="editing.id ? 'Edit goal' : 'New savings goal'" @close="editing = null">
      <form class="space-y-4" @submit.prevent="saveGoal">
        <div>
          <label class="label" for="g-name">What are you saving for?</label>
          <input id="g-name" v-model="goalForm.name" class="input" required maxlength="60" placeholder="e.g. New laptop" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label" for="g-target">Target amount</label>
            <input id="g-target" v-model="goalForm.target_amount" type="number" min="0.01" step="0.01" class="input" required />
          </div>
          <div>
            <label class="label" for="g-date">Target date <span class="font-normal text-slate-400">(optional)</span></label>
            <input id="g-date" v-model="goalForm.target_date" type="date" class="input" />
          </div>
        </div>
        <p v-if="goalError" class="alert-error">{{ goalError }}</p>
        <div class="flex justify-end gap-2">
          <button type="button" class="btn btn-secondary" @click="editing = null">Cancel</button>
          <button class="btn btn-primary" :disabled="savingGoal">{{ savingGoal ? 'Saving…' : 'Save goal' }}</button>
        </div>
      </form>
    </BaseModal>

    <!-- Add / withdraw -->
    <BaseModal
      v-if="moving"
      :title="`${moving.direction === 'add' ? 'Add money to' : 'Withdraw from'} ${moving.goal.name}`"
      @close="moving = null"
    >
      <form class="space-y-4" @submit.prevent="saveMoney">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label" for="m-amount">Amount</label>
            <input
              id="m-amount"
              v-model="moneyForm.amount"
              type="number"
              min="0.01"
              step="0.01"
              :max="moving.direction === 'withdraw' ? moving.goal.saved : undefined"
              class="input"
              required
            />
          </div>
          <div>
            <label class="label" for="m-date">Date</label>
            <input id="m-date" v-model="moneyForm.date" type="date" class="input" required />
          </div>
        </div>
        <div>
          <label class="label" for="m-note">Note <span class="font-normal text-slate-400">(optional)</span></label>
          <input id="m-note" v-model="moneyForm.note" class="input" maxlength="200" />
        </div>
        <p v-if="moving.direction === 'withdraw'" class="text-xs text-slate-500">
          {{ formatMoney(moving.goal.saved) }} available in this goal.
        </p>
        <p v-if="moneyError" class="alert-error">{{ moneyError }}</p>
        <div class="flex justify-end gap-2">
          <button type="button" class="btn btn-secondary" @click="moving = null">Cancel</button>
          <button class="btn btn-primary" :disabled="savingMoney">
            {{ savingMoney ? 'Saving…' : moving.direction === 'add' ? 'Add money' : 'Withdraw' }}
          </button>
        </div>
      </form>
    </BaseModal>
  </div>
</template>
