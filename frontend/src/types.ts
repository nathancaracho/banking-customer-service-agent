export type Session = {
  accessToken: string
  userId: string
  roles: string[]
}

export type Chat = {
  id: string
  user_id: string
  created_at: string
  updated_at: string
}

export type ChatMessage = {
  id: string
  chat_id: string
  role: 'user' | 'assistant'
  content: string
  status: string
  created_at: string
}

export type ChatDetail = Chat & {
  messages: ChatMessage[]
}

export type AgentEvent = {
  request_id: string
  chat_id: string
  type: 'chunk' | 'confirmation_required' | 'completed' | 'failed'
  sequence: number
  payload: {
    content?: string
    code?: string
    checkpoint_id?: string
  }
}

export type AdminUser = {
  id: string
  display_name: string
  is_active: boolean
  created_at: string
  roles: string[]
}

export type AvailableRole = 'customer' | 'manager' | 'admin'

export type UserRole = {
  name: AvailableRole
}

export type UserFinancialSummary = {
  user_id: string
  display_name: string
  segment: string
  credit_score: number
  balance: string
  current_limit: string
  max_eligible_limit: string
  missing_to_max_eligible: string
  increase_instructions: string
}

export type KnowledgeVersion = {
  id: string
  version: number
  status: string
  chunk_count: number
  embedding_dimensions: number
  error_message: string | null
  created_at: string
}

export type KnowledgeDocument = {
  document_id: string
  title: string
  original_file_name: string
  content_type: string
  source: string
  active: boolean
  status: string
  active_version: number
  chunk_count: number
  embedding_dimensions: number
  updated_at: string
}

export type KnowledgeDocumentDetail = KnowledgeDocument & {
  versions: KnowledgeVersion[]
}

export type KnowledgeIngestionResult = {
  ingestion_id: string
  document_id: string
  status: string
  chunk_size: number
  chunk_overlap: number
  embedding_dimensions: number
  chunk_count: number
}
