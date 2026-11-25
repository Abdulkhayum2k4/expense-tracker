// Must match the Currency list in backend/app/schemas.py.
// The locale decides digit grouping and date format (en-IN: 1,23,456.00).
export const CURRENCIES = [
  { code: 'INR', label: 'Indian rupee', locale: 'en-IN' },
  { code: 'USD', label: 'US dollar', locale: 'en-US' },
  { code: 'EUR', label: 'Euro', locale: 'en-IE' },
  { code: 'GBP', label: 'British pound', locale: 'en-GB' },
  { code: 'AED', label: 'UAE dirham', locale: 'en-AE' },
  { code: 'SAR', label: 'Saudi riyal', locale: 'en-US' },
  { code: 'SGD', label: 'Singapore dollar', locale: 'en-SG' },
  { code: 'AUD', label: 'Australian dollar', locale: 'en-AU' },
  { code: 'CAD', label: 'Canadian dollar', locale: 'en-CA' },
  { code: 'JPY', label: 'Japanese yen', locale: 'ja-JP' },
]

export const DEFAULT_CURRENCY = 'INR'

export function localeFor(code) {
  return CURRENCIES.find((c) => c.code === code)?.locale ?? 'en-IN'
}
