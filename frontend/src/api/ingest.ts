import apiClient from './client'
import type { IngestPost, IngestDetail } from './types'

export const ingestApi = {
  list: (params?: { status?: string; category?: string; skip?: number; limit?: number }) =>
    apiClient.get<IngestPost[]>('/ingest/posts', { params }),

  create: (data: {
    title?: string  // 비워두면 본문에서 자동 추출
    body_md: string
    type?: string
    priority?: string
    category?: string
    source_url?: string
    source_author?: string
    source_date?: string
  }) => apiClient.post<IngestPost>('/ingest/posts', data),

  update: (id: number, data: {
    title?: string
    body_md?: string
    type?: string
    priority?: string
    category?: string
    source_url?: string
    source_author?: string
    rerun?: boolean
  }) => apiClient.put<{ message: string; post_id: number; rerun: boolean }>(`/ingest/posts/${id}`, data),

  get: (id: number) => apiClient.get<IngestDetail>(`/ingest/posts/${id}`),

  uploadAttachment: (id: number, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return apiClient.post(`/ingest/posts/${id}/attachments`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  run: (id: number) => apiClient.post(`/ingest/posts/${id}/run`),
  retry: (id: number) => apiClient.post(`/ingest/posts/${id}/retry`),
}
