import { describe, expect, it } from 'vitest'
import { guessDateFormat, guessMapping, mapRows, parseAmount, parseDate } from './csvImport'

describe('parseDate', () => {
  it.each([
    ['2026-11-24', 'YYYY-MM-DD', '2026-11-24'],
    ['2026/1/5', 'YYYY-MM-DD', '2026-01-05'],
    ['24/11/2026', 'DD/MM/YYYY', '2026-11-24'],
    ['24-11-26', 'DD/MM/YYYY', '2026-11-24'],
    ['11/24/2026', 'MM/DD/YYYY', '2026-11-24'],
    ['2026-11-24T10:00:00', 'YYYY-MM-DD', '2026-11-24'],
  ])('%s as %s', (input, format, expected) => {
    expect(parseDate(input, format)).toBe(expected)
  })

  it.each([['31/02/2026', 'DD/MM/YYYY'], ['24/11/2026', 'MM/DD/YYYY'], ['', 'YYYY-MM-DD'], ['soon', 'YYYY-MM-DD']])(
    'rejects %s as %s',
    (input, format) => {
      expect(parseDate(input, format)).toBeNull()
    },
  )
})

describe('guessDateFormat', () => {
  it('spots ISO, day-first and month-first dates', () => {
    expect(guessDateFormat(['2026-11-01', '2026-11-24'])).toBe('YYYY-MM-DD')
    expect(guessDateFormat(['01/11/2026', '24/11/2026'])).toBe('DD/MM/YYYY')
    expect(guessDateFormat(['11/01/2026', '11/24/2026'])).toBe('MM/DD/YYYY')
  })
})

describe('parseAmount', () => {
  it.each([
    ['1,234.50', 1234.5],
    ['₹ 1,23,456.00', 123456],
    ['-250', -250],
    ['(250.00)', -250],
    ['250 Dr', -250],
    ['250.00 CR', 250],
    ['$12', 12],
  ])('%s -> %d', (input, expected) => {
    expect(parseAmount(input)).toBe(expected)
  })

  it('separates blank from unreadable', () => {
    expect(parseAmount('')).toBeNull()
    expect(parseAmount('  ')).toBeNull()
    expect(parseAmount('abc')).toBeNaN()
  })
})

describe('guessMapping', () => {
  it("recognises the app's own export", () => {
    const m = guessMapping(['date', 'title', 'type', 'category', 'amount', 'description'])
    expect(m).toMatchObject({ date: 'date', title: 'title', description: 'description', amount: 'amount', type: 'type', category: 'category', amountMode: 'type' })
  })

  it('recognises a typical bank statement with debit/credit columns', () => {
    const m = guessMapping(['Txn Date', 'Narration', 'Withdrawal Amt', 'Deposit Amt', 'Balance'])
    expect(m).toMatchObject({ date: 'Txn Date', title: 'Narration', description: '', debit: 'Withdrawal Amt', credit: 'Deposit Amt', amountMode: 'split' })
  })
})

describe('mapRows', () => {
  const defaults = { expense: 'Other', income: 'Salary' }

  it('maps a signed amount column', () => {
    const mapping = { ...guessMapping(['Date', 'Description', 'Amount']), dateFormat: 'DD/MM/YYYY' }
    const { valid, problems } = mapRows(
      [
        { Date: '24/11/2026', Description: 'Lunch', Amount: '-250.50' },
        { Date: '01/11/2026', Description: 'Pay', Amount: '60,000' },
      ],
      mapping,
      defaults,
    )
    expect(problems).toEqual([])
    expect(valid).toEqual([
      { line: 2, tx: { date: '2026-11-24', title: 'Lunch', amount: 250.5, type: 'expense', category: 'Other', description: '' } },
      { line: 3, tx: { date: '2026-11-01', title: 'Pay', amount: 60000, type: 'income', category: 'Salary', description: '' } },
    ])
  })

  it('maps debit/credit columns and reports bad rows with their file line', () => {
    const mapping = { ...guessMapping(['Date', 'Narration', 'Debit', 'Credit']), dateFormat: 'DD/MM/YYYY' }
    const { valid, problems } = mapRows(
      [
        { Date: '05/11/2026', Narration: 'ATM', Debit: '2,000.00', Credit: '' },
        { Date: '06/11/2026', Narration: 'Refund', Debit: '', Credit: '300' },
        { Date: '31/11/2026', Narration: 'Bad date', Debit: '1', Credit: '' },
        { Date: '07/11/2026', Narration: 'Both', Debit: '1', Credit: '1' },
        { Date: '08/11/2026', Narration: 'Neither', Debit: '', Credit: '' },
        { Date: '09/11/2026', Narration: '', Debit: '5', Credit: '' },
      ],
      mapping,
      defaults,
    )
    expect(valid.map((v) => [v.tx.title, v.tx.type, v.tx.amount])).toEqual([
      ['ATM', 'expense', 2000],
      ['Refund', 'income', 300],
    ])
    expect(problems.map((p) => p.line)).toEqual([4, 5, 6, 7])
    expect(problems[0].message).toMatch(/Unreadable date/)
  })

  it("round-trips the app's own export, including formula-guarded titles", () => {
    const mapping = guessMapping(['date', 'title', 'type', 'category', 'amount', 'description'])
    const { valid, problems } = mapRows(
      [
        { date: '2026-11-24', title: "'=SUM(1)", type: 'expense', category: 'Food', amount: '250.5', description: 'team' },
        { date: '2026-11-01', title: 'Salary', type: 'income', category: 'Salary', amount: '60000.0', description: '' },
        { date: '2026-11-02', title: 'Odd', type: 'transfer', category: 'Food', amount: '1', description: '' },
      ],
      mapping,
      defaults,
    )
    expect(valid[0].tx).toEqual({ date: '2026-11-24', title: '=SUM(1)', amount: 250.5, type: 'expense', category: 'Food', description: 'team' })
    expect(valid[1].tx.category).toBe('Salary')
    expect(problems).toEqual([{ line: 4, message: 'Unknown type "transfer" (use income or expense)' }])
  })
})
