import { computed, ref } from 'vue'

// 'light' | 'dark' | 'system'. index.html applies the stored choice before the
// first paint (no white flash); this store keeps it in sync afterwards.
const KEY = 'expense_tracker_theme'
const media = window.matchMedia('(prefers-color-scheme: dark)')

const preference = ref(localStorage.getItem(KEY) || 'system')
const systemDark = ref(media.matches)

const isDark = computed(() => preference.value === 'dark' || (preference.value === 'system' && systemDark.value))

function apply() {
  document.documentElement.classList.toggle('dark', isDark.value)
  document.documentElement.style.colorScheme = isDark.value ? 'dark' : 'light'
}
apply()

export const theme = {
  preference,
  isDark,
  set(value) {
    preference.value = value
    localStorage.setItem(KEY, value)
    apply()
  },
}

media.addEventListener('change', (e) => {
  systemDark.value = e.matches
  apply()
})
