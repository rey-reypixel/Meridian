import { api } from './client'
import type { User } from './types'

export async function getLoginUrl(): Promise<string> {
  const { auth_url } = await api.get<{ auth_url: string }>('/auth/login')
  return auth_url
}

export async function getCurrentUser(): Promise<User> {
  return api.get<User>('/auth/me')
}
