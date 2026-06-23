import { create } from 'zustand'
import { clearToken, getToken } from '../api/client'

interface AuthState {
  isAuthenticated: boolean
  setAuthenticated: (v: boolean) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: !!getToken(),
  setAuthenticated: (v) => set({ isAuthenticated: v }),
  logout: () => {
    clearToken()
    set({ isAuthenticated: false })
  },
}))
