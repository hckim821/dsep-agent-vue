import apiClient from './client'
import type { SchemaVersion } from './types'

export const schemaApi = {
  getCurrent: () => apiClient.get<SchemaVersion>('/schema/current'),
  update: (content: string, note?: string) =>
    apiClient.put<SchemaVersion>('/schema/current', { content, note }),
  listVersions: () => apiClient.get<SchemaVersion[]>('/schema/versions'),
}
