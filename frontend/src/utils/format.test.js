import { describe, expect, it } from 'vitest'
import { formatDate, formatMoney, monthLabel, parseMonthValue } from './format'

describe('formatMoney', () => {
  it('uses Indian digit grouping and the rupee sign by default', () => {
    expect(formatMoney(123456.5)).toBe('₹1,23,456.50')
  })
  it('treats missing values as zero', () => {
    expect(formatMoney(undefined)).toBe('₹0.00')
  })
})

describe('formatDate', () => {
  it('formats a calendar date without shifting it by timezone', () => {
    expect(formatDate('2026-11-01')).toBe('1 Nov 2026')
    expect(formatDate('2026-12-31')).toBe('31 Dec 2026')
  })
})

describe('months', () => {
  it('parses <input type="month"> values', () => {
    expect(parseMonthValue('2026-02')).toEqual({ year: 2026, month: 2 })
  })
  it('labels a month', () => {
    expect(monthLabel(11, 2026)).toBe('November 2026')
  })
})
