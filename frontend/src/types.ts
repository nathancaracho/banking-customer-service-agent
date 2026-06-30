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
  }
}
