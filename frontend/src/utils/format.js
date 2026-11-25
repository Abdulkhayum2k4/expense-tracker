import { auth } from '@/stores/auth'
import { DEFAULT_CURRENCY, localeFor } from './currencies'

// Reading auth.state.user here makes every template that formats money
// re-render when the user changes their currency in Settings.
function currentCurrency() {
  return auth.state.user?.currency || DEFAULT_CURRENCY
}

function currentLocale() {
  return localeFor(currentCurrency())
}

const cache = new Map()
function formatter(kind) {
  const currency = currentCurrency()
  const key = `${kind}:${currency}`
  if (!cache.has(key)) {
    const options = { style: 'currency', currency }
    if (kind === 'compact') Object.assign(options, { notation: 'compact', maximumFractionDigits: 1 })
    cache.set(key, new Intl.NumberFormat(localeFor(currency), options))
  }
  return cache.get(key)
}

export const formatMoney = (value) => formatter('full').format(value ?? 0)
export const formatMoneyCompact = (value) => formatter('compact').format(value ?? 0)

/** The currency's symbol, e.g. "₹" or "$". */
export function currencySymbol() {
  return formatter('full').formatToParts(0).find((p) => p.type === 'currency')?.value ?? currentCurrency()
}

/** "2026-11-24" -> "24 Nov 2026" (parsed as a calendar date, not shifted by timezone). */
export function formatDate(isoDate) {
  const [y, m, d] = isoDate.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString(currentLocale(), { day: 'numeric', month: 'short', year: 'numeric' })
}

export const MONTH_NAMES = Array.from({ length: 12 }, (_, i) =>
  new Date(2000, i, 1).toLocaleDateString('en-GB', { month: 'short' }),
)

export function monthLabel(month, year) {
  return new Date(year, month - 1, 1).toLocaleDateString('en-GB', { month: 'long', year: 'numeric' })
}

/** Today's date as YYYY-MM-DD in the user's local timezone. */
export function todayIso() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** Current month as YYYY-MM, the value format of <input type="month">. */
export function currentMonthValue() {
  return todayIso().slice(0, 7)
}

export function parseMonthValue(value) {
  const [year, month] = value.split('-').map(Number)
  return { year, month }
}
