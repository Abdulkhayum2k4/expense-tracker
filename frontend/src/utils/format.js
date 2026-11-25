const LOCALE = import.meta.env.VITE_LOCALE || 'en-IN'
const CURRENCY = import.meta.env.VITE_CURRENCY || 'INR'

const money = new Intl.NumberFormat(LOCALE, { style: 'currency', currency: CURRENCY })
const moneyCompact = new Intl.NumberFormat(LOCALE, {
  style: 'currency',
  currency: CURRENCY,
  notation: 'compact',
  maximumFractionDigits: 1,
})

export const formatMoney = (value) => money.format(value ?? 0)
export const formatMoneyCompact = (value) => moneyCompact.format(value ?? 0)

/** "2026-11-24" -> "24 Nov 2026" (parsed as a calendar date, not shifted by timezone). */
export function formatDate(isoDate) {
  const [y, m, d] = isoDate.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString(LOCALE, { day: 'numeric', month: 'short', year: 'numeric' })
}

export const MONTH_NAMES = Array.from({ length: 12 }, (_, i) =>
  new Date(2000, i, 1).toLocaleDateString(LOCALE, { month: 'short' }),
)

export function monthLabel(month, year) {
  return new Date(year, month - 1, 1).toLocaleDateString(LOCALE, { month: 'long', year: 'numeric' })
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
