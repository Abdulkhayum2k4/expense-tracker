import { computed, reactive } from 'vue'

const TOKEN_KEY = 'expense_tracker_token'
const USER_KEY = 'expense_tracker_user'

function readUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY))
  } catch {
    return null
  }
}

const state = reactive({
  token: localStorage.getItem(TOKEN_KEY),
  user: readUser(),
})

export const auth = {
  state,
  isAuthenticated: computed(() => Boolean(state.token)),

  /** Store the response of /auth/login or /auth/register. */
  setSession({ access_token, user }) {
    state.token = access_token
    state.user = user
    localStorage.setItem(TOKEN_KEY, access_token)
    localStorage.setItem(USER_KEY, JSON.stringify(user))
  },

  logout() {
    state.token = null
    state.user = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  },
}
