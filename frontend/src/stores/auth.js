import { computed, reactive } from 'vue'

// The session itself lives in an httpOnly cookie that JavaScript can't read.
// Only the user's profile is cached here, so the UI can render before /auth/me answers.
const USER_KEY = 'expense_tracker_user'
localStorage.removeItem('expense_tracker_token') // left over from the localStorage-token version

function readUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY))
  } catch {
    return null
  }
}

const state = reactive({ user: readUser() })

export const auth = {
  state,
  isAuthenticated: computed(() => Boolean(state.user)),

  setUser(user) {
    state.user = user
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
    else localStorage.removeItem(USER_KEY)
  },

  /** Store the response of /auth/login or /auth/register. */
  setSession({ user }) {
    this.setUser(user)
  },

  /** Forget the user locally (the server-side cookie is cleared by /auth/logout). */
  clear() {
    this.setUser(null)
  },
}
