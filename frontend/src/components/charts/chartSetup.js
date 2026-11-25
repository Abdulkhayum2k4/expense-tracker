import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  Tooltip,
} from 'chart.js'

ChartJS.register(BarElement, CategoryScale, LinearScale, Tooltip, Legend)

// Validated categorical palette, slots 1 and 2. Income and expense keep these
// colours on every chart, so the same colour always means the same thing.
export const COLORS = {
  income: '#257de0',
  expense: '#f47230',
  // Net savings: sign is carried by position above/below zero; colour only reinforces it.
  surplus: '#008a17',
  deficit: '#ec4647',
  grid: '#e7e7e7',
  axis: '#c2c2c2',
  textSecondary: '#666666',
}

ChartJS.defaults.font.family = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'
ChartJS.defaults.font.size = 12
ChartJS.defaults.color = COLORS.textSecondary
ChartJS.defaults.plugins.tooltip.backgroundColor = '#191919'
ChartJS.defaults.plugins.tooltip.padding = 10
ChartJS.defaults.plugins.tooltip.cornerRadius = 6
ChartJS.defaults.plugins.tooltip.boxPadding = 4
