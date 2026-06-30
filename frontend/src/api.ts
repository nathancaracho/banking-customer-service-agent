import type {
  AdminUser,
  AgentEvent,
  Chat,
  ChatDetail,
  KnowledgeDocument,
  KnowledgeDocumentDetail,
  KnowledgeIngestionResult,
  Session,
  UserFinancialSummary,
  UserRole,
} from '@/types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8200'
const IDENTITY_URL =
  import.meta.env.VITE_IDENTITY_URL ?? 'http://localhost:8100'

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
  baseUrl?: string,
): Promise<T> {
  const headers = new Headers(options.headers)

  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${baseUrl ?? API_URL}${path}`, {
    ...options,
    headers: {
      ...Object.fromEntries(headers.entries()),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? `HTTP ${response.status}`)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

export async function login(
  username: string,
  password: string,
): Promise<Session> {
  const response = await request<{
    access_token: string
    user_id: string
    roles: string[]
  }>('/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })

  return {
    accessToken: response.access_token,
    userId: response.user_id,
    roles: response.roles,
  }
}

export function listChats(token: string): Promise<Chat[]> {
  return request('/v1/chats', {}, token)
}

export function createChat(token: string): Promise<Chat> {
  return request('/v1/chats', { method: 'POST' }, token)
}

export function getChat(token: string, chatId: string): Promise<ChatDetail> {
  return request(`/v1/chats/${chatId}`, {}, token)
}

export async function streamMessage(
  token: string,
  chatId: string,
  content: string,
  onEvent: (event: AgentEvent) => void,
): Promise<void> {
  const response = await fetch(`${API_URL}/v1/chats/${chatId}/messages`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ content }),
  })

  if (!response.ok || !response.body) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? `HTTP ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()

    if (done) break

    buffer += decoder.decode(value, { stream: true })
    let boundary = buffer.indexOf('\n\n')

    while (boundary >= 0) {
      const block = buffer.slice(0, boundary)
      buffer = buffer.slice(boundary + 2)

      for (const line of block.split('\n')) {
        if (line.startsWith('data: ')) {
          onEvent(JSON.parse(line.slice(6)) as AgentEvent)
        }
      }

      boundary = buffer.indexOf('\n\n')
    }
  }
}

export async function listUsers(
  token: string,
): Promise<AdminUser[]> {
  return request('/v1/admin/users', {}, token, IDENTITY_URL)
}

export async function getUserRoles(
  token: string,
  userId: string,
): Promise<UserRole[]> {
  return request(`/v1/admin/users/${userId}/roles`, {}, token, IDENTITY_URL)
}

export async function getUserFinancialSummary(
  token: string,
  userId: string,
): Promise<UserFinancialSummary> {
  return request(
    `/v1/admin/users/${userId}/financial-summary`,
    {},
    token,
    API_URL,
  )
}

export async function updateUserRoles(
  token: string,
  userId: string,
  roles: string[],
): Promise<void> {
  await request(
    `/v1/admin/users/${userId}/roles`,
    { method: 'PUT', body: JSON.stringify({ roles }) },
    token,
    IDENTITY_URL,
  )
}

export async function confirmAction(
  token: string,
  chatId: string,
  checkpointId: string,
  confirmed: boolean,
): Promise<{ status: string }> {
  return request(`/v1/chats/${chatId}/confirm`, {
    method: 'POST',
    body: JSON.stringify({ checkpoint_id: checkpointId, confirmed }),
  }, token)
}

export function listKnowledgeDocuments(
  token: string,
): Promise<KnowledgeDocument[]> {
  return request('/v1/knowledge/documents', {}, token)
}

export function getKnowledgeDocument(
  token: string,
  documentId: string,
): Promise<KnowledgeDocumentDetail> {
  return request(`/v1/knowledge/documents/${documentId}`, {}, token)
}

export async function uploadKnowledgeDocument(
  token: string,
  payload: {
    file: File
    title?: string
    source?: string
    active: boolean
  },
): Promise<KnowledgeIngestionResult> {
  const body = new FormData()
  body.set('file', payload.file)
  body.set('active', String(payload.active))
  if (payload.title?.trim()) body.set('title', payload.title.trim())
  if (payload.source?.trim()) body.set('source', payload.source.trim())

  return request('/v1/knowledge/documents', { method: 'POST', body }, token)
}

export async function reprocessKnowledgeDocument(
  token: string,
  documentId: string,
  payload: {
    file: File
    title?: string
    source?: string
  },
): Promise<KnowledgeIngestionResult> {
  const body = new FormData()
  body.set('file', payload.file)
  if (payload.title?.trim()) body.set('title', payload.title.trim())
  if (payload.source?.trim()) body.set('source', payload.source.trim())

  return request(
    `/v1/knowledge/documents/${documentId}/reprocess`,
    { method: 'POST', body },
    token,
  )
}

export async function updateKnowledgeDocumentStatus(
  token: string,
  documentId: string,
  active: boolean,
): Promise<KnowledgeDocumentDetail> {
  return request(
    `/v1/knowledge/documents/${documentId}/status`,
    { method: 'PATCH', body: JSON.stringify({ active }) },
    token,
  )
}

export async function deleteKnowledgeDocument(
  token: string,
  documentId: string,
): Promise<void> {
  await request(
    `/v1/knowledge/documents/${documentId}`,
    { method: 'DELETE' },
    token,
  )
}
