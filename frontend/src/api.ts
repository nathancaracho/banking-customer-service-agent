import type { AgentEvent, Chat, ChatDetail, Session } from '@/types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8200'

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? `HTTP ${response.status}`)
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
