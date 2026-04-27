import apiClient from './client'
import type { ChatSession, ChatMessage } from './types'

export const chatApi = {
  listSessions: () => apiClient.get<ChatSession[]>('/chat/sessions'),
  createSession: (title?: string) => apiClient.post<ChatSession>('/chat/sessions', { title }),
  getMessages: (sessionId: number) => apiClient.get<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`),
  toIngest: (sessionId: number) => apiClient.post<{ post_id: number }>(`/chat/sessions/${sessionId}/to-ingest`),
}
