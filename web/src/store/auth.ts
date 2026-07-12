import { createContext, useContext } from 'react'
import type { User } from '../api/auth'

export interface AuthState {
  user: User | null
  token: string | null
  setAuth: (token: string, user: User) => void
  logout: () => void
}

export const AuthContext = createContext<AuthState>({
  user: null,
  token: null,
  setAuth: () => {},
  logout: () => {},
})

export function useAuth() {
  return useContext(AuthContext)
}
