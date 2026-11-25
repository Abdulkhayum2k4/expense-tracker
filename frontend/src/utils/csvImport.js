/**
 * Turn rows from a parsed CSV (objects keyed by header) into transactions the
 * API accepts, using a column mapping the user confirms. Pure: no Vue, no network.
 */

export const DATE_FORMATS = [
  { value: 'YYYY-MM-DD', label: 'YYYY-MM-DD (2026-11-24)' },
  { value: 'DD/MM/YYYY', label: 'DD/MM/YYYY (24/11/2026)' },
  { value: 'MM/DD/YYYY', label: 'MM/DD/YYYY (11/24/2026)' },
]

export const AMOUNT_MODES = [
  { value: 'signed', label: 'One amount column: negative = expense, positive = income' },
  { value: 'split', label: 'Separate debit (expense) and credit (income) columns' },
  { value: 'type', label: 'Amount column plus a type column (income / expense)' },
]

/** Column names banks and spreadsheets commonly use, lower-case. */
const HINTS = {
  date: ['date', 'transaction date', 'txn date', 'value date', 'posting date', 'booking date'],
  title: ['title', 'description', 'narration', 'details', 'particulars', 'payee', 'merchant', 'name', 'remarks'],
  description: ['description', 'notes', 'note', 'memo', 'remarks'],
  amount: ['amount', 'value', 'transaction amount', 'amount (inr)'],
  debit: ['debit', 'withdrawal', 'withdrawal amt', 'withdrawal amount', 'debit amount', 'dr', 'paid out', 'money out'],
  credit: ['credit', 'deposit', 'deposit amt', 'deposit amount', 'credit amount', 'cr', 'paid in', 'money in'],
  type: ['type', 'transaction type', 'dr/cr', 'cr/dr'],
  category: ['category', 'categories'],
}

/** Best-guess mapping from the file's headers. Empty string = not mapped. */
export function guessMapping(headers) {
  const lower = headers.map((h) => h.trim().toLowerCase())
  const pick = (key, exclude = []) => {
    for (const hint of HINTS[key]) {
      const i = lower.indexOf(hint)
      if (i !== -1 && !exclude.includes(headers[i])) return headers[i]
    }
    return ''
  }
  const title = pick('title')
  const mapping = {
    date: pick('date'),
    title,
    description: pick('description', [title]),
    amount: pick('amount'),
    debit: pick('debit'),
    credit: pick('credit'),
    type: pick('type'),
    category: pick('category'),
    dateFormat: 'YYYY-MM-DD',
    amountMode: 'signed',
  }
  if (mapping.debit && mapping.credit) mapping.amountMode = 'split'
  else if (mapping.amount && mapping.type) mapping.amountMode = 'type'
  return mapping
}

/** Guess the date format from sample values (falls back to YYYY-MM-DD). */
export function guessDateFormat(samples) {
  const values = samples.map((s) => String(s ?? '').trim()).filter(Boolean)
  if (values.length && values.every((v) => /^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}/.test(v))) return 'YYYY-MM-DD'
  const parts = values.map((v) => v.split(/[-/.\s]/).map(Number))
  if (parts.some((p) => p[0] > 12)) return 'DD/MM/YYYY'
  if (parts.some((p) => p[1] > 12)) return 'MM/DD/YYYY'
  return values.length && /^\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}/.test(values[0]) ? 'DD/MM/YYYY' : 'YYYY-MM-DD'
}

/** Parse a date string in the given format to YYYY-MM-DD, or null if it isn't a real date. */
export function parseDate(value, format) {
  const text = String(value ?? '').trim()
  const parts = text.split(/[-/.\sT]/).filter(Boolean)
  if (parts.length < 3) return null
  let y, m, d
  if (format === 'YYYY-MM-DD') [y, m, d] = parts
  else if (format === 'DD/MM/YYYY') [d, m, y] = parts
  else [m, d, y] = parts
  ;[y, m, d] = [y, m, d].map((p) => Number(p))
  if (![y, m, d].every(Number.isInteger)) return null
  if (y < 100) y += 2000
  const date = new Date(Date.UTC(y, m - 1, d))
  if (date.getUTCFullYear() !== y || date.getUTCMonth() !== m - 1 || date.getUTCDate() !== d) return null
  return `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`
}

/**
 * Parse an amount like "1,234.50", "₹ 1,234.50", "-250", "(250.00)" or "250 Dr".
 * Returns a number (negative for "(x)", "-x" or a "Dr" suffix), null if blank, NaN if unreadable.
 */
export function parseAmount(value) {
  let text = String(value ?? '').trim()
  if (!text) return null
  let negative = false
  if (/^\(.*\)$/.test(text)) {
    negative = true
    text = text.slice(1, -1)
  }
  if (/\s*dr\.?$/i.test(text)) {
    negative = true
    text = text.replace(/\s*dr\.?$/i, '')
  } else {
    text = text.replace(/\s*cr\.?$/i, '')
  }
  text = text.replace(/[^\d.,-]/g, '').replace(/,/g, '')
  if (text.startsWith('-')) {
    negative = !negative
    text = text.slice(1)
  }
  if (!/^\d+(\.\d+)?$/.test(text)) return NaN
  const n = Number(text)
  return negative ? -n : n
}

const INCOME_WORDS = ['income', 'credit', 'cr', 'deposit', 'in']
const EXPENSE_WORDS = ['expense', 'debit', 'dr', 'withdrawal', 'out']

function typeFromWord(word) {
  const w = String(word ?? '').trim().toLowerCase()
  if (INCOME_WORDS.includes(w)) return 'income'
  if (EXPENSE_WORDS.includes(w)) return 'expense'
  return null
}

/** Our own export guards formula-like cells with a leading apostrophe; undo that. */
function cleanText(value) {
  const text = String(value ?? '').trim()
  return /^'[=+\-@]/.test(text) ? text.slice(1) : text
}

/**
 * @param rows      array of objects from Papa.parse({ header: true })
 * @param mapping   from guessMapping(), edited by the user
 * @param defaults  { expense: 'Other', income: 'Other' } category for rows without one
 * @returns { valid: [{ line, tx }], problems: [{ line, message }] }
 *          `line` is the row number in the file, counting the header as line 1.
 */
export function mapRows(rows, mapping, defaults = { expense: 'Other', income: 'Other' }) {
  const valid = []
  const problems = []

  rows.forEach((row, index) => {
    const line = index + 2
    const fail = (message) => problems.push({ line, message })

    const date = parseDate(row[mapping.date], mapping.dateFormat)
    if (!date) return fail(`Unreadable date "${row[mapping.date] ?? ''}" (expected ${mapping.dateFormat})`)

    let amount
    let type
    if (mapping.amountMode === 'split') {
      const debit = parseAmount(row[mapping.debit])
      const credit = parseAmount(row[mapping.credit])
      if (Number.isNaN(debit) || Number.isNaN(credit)) return fail('Unreadable debit/credit amount')
      if (debit && credit) return fail('Row has both a debit and a credit amount')
      if (!debit && !credit) return fail('Row has no amount')
      ;[amount, type] = debit ? [Math.abs(debit), 'expense'] : [Math.abs(credit), 'income']
    } else {
      const value = parseAmount(row[mapping.amount])
      if (value === null) return fail('Row has no amount')
      if (Number.isNaN(value)) return fail(`Unreadable amount "${row[mapping.amount]}"`)
      if (value === 0) return fail('Amount is zero')
      if (mapping.amountMode === 'type') {
        type = typeFromWord(row[mapping.type])
        if (!type) return fail(`Unknown type "${row[mapping.type] ?? ''}" (use income or expense)`)
        amount = Math.abs(value)
      } else {
        type = value < 0 ? 'expense' : 'income'
        amount = Math.abs(value)
      }
    }

    const title = cleanText(row[mapping.title]).slice(0, 100)
    if (!title) return fail('Row has no title')

    const description = mapping.description && mapping.description !== mapping.title
      ? cleanText(row[mapping.description]).slice(0, 500)
      : ''
    const category = (mapping.category && cleanText(row[mapping.category]).slice(0, 50)) || defaults[type]

    valid.push({ line, tx: { date, title, amount: Math.round(amount * 100) / 100, type, category, description } })
  })

  return { valid, problems }
}
