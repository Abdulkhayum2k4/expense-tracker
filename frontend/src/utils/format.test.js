import { afterEach, describe, expect, it } from 'vitest'
import { auth } from '@/stores/auth'
import { currencySymbol, formatDate, formatMoney, monthLabel, parseMonthValue } from './format'

afterEach(() => auth.clear())

describe('formatMoney', () => {
  it('uses Indian digit grouping and the rupee sign by default', () => {
    expect(formatMoney(123456.5)).toBe('₹1,23,456.50')
    expect(currencySymbol()).toBe('₹')
  })
  it('treats missing values as zero', () => {
    expect(formatMoney(undefined)).toBe('₹0.00')
  })
  it("follows the user's currency", () => {
    auth.setUser({ name: 'A', currency: 'USD' })
    expect(formatMoney(123456.5)).toBe('$123,456.50')
    expect(currencySymbol()).toBe('$')
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
