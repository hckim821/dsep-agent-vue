import apiClient from './client'
import type { WikiPage, WikiPageDetail, SearchResult } from './types'

export const wikiApi = {
  listPages: (category?: string) =>
    apiClient.get<WikiPage[]>('/wiki/pages', { params: category ? { category } : {} }),

  getTree: () => apiClient.get<Record<string, any>>('/wiki/tree'),

  getByPath: (path: string) =>
    apiClient.get<WikiPageDetail>('/wiki/pages/by-path', { params: { path } }),

  getBacklinks: (pageId: number) =>
    apiClient.get<WikiPage[]>(`/wiki/pages/${pageId}/backlinks`),

  getSources: (pageId: number) =>
    apiClient.get<{ relation: string; post_id: number; title: string; created_at: string }[]>(
      `/wiki/pages/${pageId}/sources`
    ),

  search: (q: string) =>
    apiClient.get<SearchResult[]>('/wiki/search', { params: { q } }),
}
