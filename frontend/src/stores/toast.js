import { reactive } from 'vue'

// kind: 'success' | 'warning' | 'error'
const toasts = reactive([])
let nextId = 1

export const toast = {
  items: toasts,

  show(message, { kind = 'success', timeout = 4000 } = {}) {
    const id = nextId++
    toasts.push({ id, message, kind })
    if (timeout) setTimeout(() => this.dismiss(id), timeout)
    return id
  },

  dismiss(id) {
    const i = toasts.findIndex((t) => t.id === id)
    if (i !== -1) toasts.splice(i, 1)
  },
}
