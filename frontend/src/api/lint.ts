import apiClient from './client'
import type { LintFinding } from './types'

export const lintApi = {
  listFindings: (params?: { type?: string; severity?: string; resolved?: boolean; skip?: number; limit?: number }) =>
    apiClient.get<LintFinding[]>('/lint/findings', { params }),

  runLint: (checkTypes?: string[]) =>
    apiClient.post<{ message: string; total: number; by_type: Record<string, number> }>(
      '/lint/run',
      checkTypes ? { check_types: checkTypes } : {},
    ),
}
