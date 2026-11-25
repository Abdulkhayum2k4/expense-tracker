import { computed } from 'vue'
import { BarElement, CategoryScale, Chart as ChartJS, Legend, LinearScale, Tooltip } from 'chart.js'
import { theme } from '@/stores/theme'

ChartJS.register(BarElement, CategoryScale, LinearScale, Tooltip, Legend)

ChartJS.defaults.font.family = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'
ChartJS.defaults.font.size = 12
ChartJS.defaults.plugins.tooltip.padding = 10
ChartJS.defaults.plugins.tooltip.cornerRadius = 6
ChartJS.defaults.plugins.tooltip.boxPadding = 4

// Validated categorical palette, slots 1 and 2. Income and expense keep these
// colours on every chart, so the same colour always means the same thing.
// Dark mode uses the palette's own dark steps, not an automatic inversion.
const LIGHT = {
  income: '#257de0',
  expense: '#f47230',
  // Net savings: the sign is carried by position above/below zero; colour only reinforces it.
  surplus: '#6a4ce2', // violet: passes CVD separation against red (green does not)
  deficit: '#ec4647',
  grid: '#e7e7e7',
  axis: '#c2c2c2',
  text: '#666666',
  textStrong: '#191919',
  surface: '#ffffff',
  tooltipBg: '#191919',
  tooltipText: '#ffffff',
}

const DARK = {
  income: '#338ced',
  expense: '#e76624',
  surplus: '#9887ef',
  deficit: '#eb6263',
  grid: '#303030',
  axis: '#474747',
  text: '#9c9c9c',
  textStrong: '#efefef',
  surface: '#0f172b', // matches --color-surface in dark mode (slate-900)
  tooltipBg: '#efefef',
  tooltipText: '#191919',
}

/** Reactive chart colours for the current theme. */
export function useChartColors() {
  return computed(() => (theme.isDark.value ? DARK : LIGHT))
}

/** Tooltip styling shared by every chart. */
export function tooltipTheme(c) {
  return { backgroundColor: c.tooltipBg, titleColor: c.tooltipText, bodyColor: c.tooltipText }
}
