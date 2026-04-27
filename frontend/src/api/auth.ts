import apiClient from './client'
import type { User } from './types'

export const authApi = {
  login: (email: string, password: string) =>
    apiClient.post<{ access_token: string; token_type: string }>('/auth/login', { email, password }),

  me: () => apiClient.get<User>('/auth/me'),

  register: (email: string, password: string, display_name: string) =>
    apiClient.post<User>('/auth/register', { email, password, display_name }),
}
