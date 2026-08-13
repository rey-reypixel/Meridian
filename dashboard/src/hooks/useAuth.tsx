import { createContext, useContext, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getCurrentUser, getLoginUrl } from '@/api/auth'
import { getToken, clearToken } from '@/api/client'
import type { User } from '@/api/types'

interface AuthContextValue {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: () => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const hasToken = !!getToken()

  // isPending (not isLoading) - isLoading is isPending && isFetching, which
  // races when `enabled` flips false->true: isPending goes true immediately
  // but isFetching lags a render behind, so isLoading reads false for one
  // tick and ProtectedRoute redirects to /login before the fetch even starts.
  const { data: user, isPending } = useQuery({
    queryKey: ['currentUser'],
    queryFn: getCurrentUser,
    enabled: hasToken,
    retry: false,
  })

  const login = async () => {
    const url = await getLoginUrl()
    window.location.href = url
  }

  const logout = () => {
    clearToken()
    queryClient.clear()
    window.location.href = '/login'
  }

  return (
    <AuthContext.Provider
      value={{
        user: user ?? null,
        isLoading: hasToken && isPending,
        isAuthenticated: !!user,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
