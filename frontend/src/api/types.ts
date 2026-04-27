export interface User {
  id: number
  email: string
  display_name: string
  role: 'admin' | 'editor' | 'viewer'
}

export interface IngestPost {
  id: number
  title: string
  body_md: string
  type: 'new' | 'correction' | 'chat_summary'
  priority: 'normal' | 'urgent'
  category: string | null
  status: 'pending' | 'ocr_running' | 'ocr_done' | 'ingest_running' | 'ingest_done' | 'done' | 'failed'
  source_url: string | null
  source_author: string | null
  source_date: string | null
  unverified: boolean
  created_at: string
  updated_at: string
  author_id: number
}

export interface IngestJob {
  id: number
  stage: 'ocr' | 'ingest' | 'lint'
  status: 'running' | 'success' | 'failed'
  started_at: string
  finished_at: string | null
  tokens_used: number | null
  model_used: string | null
  log_text: string | null
  error_text: string | null
}

export interface WikiPageRef {
  id: number
  path: string
  title: string
  relation: 'created' | 'updated'
}

export interface IngestDetail {
  post: IngestPost
  jobs: IngestJob[]
  wiki_pages: WikiPageRef[]
}

export interface ChatSession {
  id: number
  title: string | null
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  citations_json: any
  created_at: string
}

export interface WikiPage {
  id: number
  path: string
  title: string
  category: string | null
  summary: string | null
  current_commit_sha: string | null
  last_ingest_id: number | null
  updated_at: string
}

export interface WikiPageDetail extends WikiPage {
  content: string | null
}

export interface SearchResult {
  page_id: number
  path: string
  title: string
  snippet: string
}

export interface LintFinding {
  id: number
  type: 'contradiction' | 'orphan' | 'stale' | 'missing_entity' | 'broken_link'
  page_ids_json: number[] | null
  description: string | null
  severity: 'low' | 'medium' | 'high'
  detected_at: string
  resolved_at: string | null
}

export interface SchemaVersion {
  id: number
  content: string
  updated_by: number
  updated_at: string
  note: string | null
}
