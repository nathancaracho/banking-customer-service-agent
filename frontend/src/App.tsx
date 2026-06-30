import {
  AssistantRuntimeProvider,
  type AppendMessage,
  useExternalStoreRuntime,
} from '@assistant-ui/react'
import { BotIcon, LogOutIcon, MessageSquareIcon, PlusIcon } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { createChat, getChat, listChats, login, streamMessage } from '@/api'
import { Thread } from '@/components/assistant-ui/thread'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { TooltipProvider } from '@/components/ui/tooltip'
import type { AgentEvent, Chat, ChatDetail, Session } from '@/types'

type UiMessageBase = {
  id: string
  content: string
  createdAt: Date
}

type UiMessage =
  | (UiMessageBase & {
      role: 'user'
    })
  | (UiMessageBase & {
      role: 'assistant'
  status:
    | { type: 'running' }
    | { type: 'complete'; reason: 'stop' }
    | { type: 'incomplete'; reason: 'error'; error: string }
    })

const SESSION_KEY = 'banking-assistant-session'

function App() {
  const [session, setSession] = useState<Session | null>(() => {
    const stored = localStorage.getItem(SESSION_KEY)
    return stored ? (JSON.parse(stored) as Session) : null
  })

  const handleLogin = (nextSession: Session) => {
    localStorage.setItem(SESSION_KEY, JSON.stringify(nextSession))
    setSession(nextSession)
  }

  const handleLogout = () => {
    localStorage.removeItem(SESSION_KEY)
    setSession(null)
  }

  return (
    <TooltipProvider>
      {session ? (
        <ChatWorkspace session={session} onLogout={handleLogout} />
      ) : (
        <LoginPage onLogin={handleLogin} />
      )}
    </TooltipProvider>
  )
}

function LoginPage({ onLogin }: { onLogin: (session: Session) => void }) {
  const [username, setUsername] = useState('customer')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setError('')

    try {
      onLogin(await login(username, password))
    } catch (loginError) {
      setError(
        loginError instanceof Error ? loginError.message : 'Falha no login',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="flex min-h-svh items-center justify-center bg-muted/40 p-6">
      <Card className="w-full max-w-md shadow-xl">
        <CardHeader className="space-y-4">
          <div className="flex size-12 items-center justify-center rounded-2xl bg-orange-500 text-white">
            <BotIcon className="size-7" />
          </div>
          <div>
            <CardTitle className="text-2xl">Atendimento inteligente</CardTitle>
            <CardDescription>
              Entre para acessar seu assistente bancário.
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <form className="space-y-5" onSubmit={submit}>
            <div className="space-y-2">
              <Label htmlFor="profile">Perfil de demonstração</Label>
              <Select value={username} onValueChange={setUsername}>
                <SelectTrigger id="profile" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="customer">Cliente</SelectItem>
                  <SelectItem value="manager">Gerente</SelectItem>
                  <SelectItem value="admin">Administrador</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Senha</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Digite a senha de demonstração"
                autoComplete="current-password"
              />
              <p className="text-xs text-muted-foreground">
                Ambiente local: use a senha <strong>demo</strong>.
              </p>
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button className="w-full" disabled={loading}>
              {loading ? 'Entrando...' : 'Entrar'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  )
}

function ChatWorkspace({
  session,
  onLogout,
}: {
  session: Session
  onLogout: () => void
}) {
  const [chats, setChats] = useState<Chat[]>([])
  const [activeChat, setActiveChat] = useState<ChatDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const refreshChats = useCallback(async () => {
    const nextChats = await listChats(session.accessToken)
    setChats(nextChats)
    return nextChats
  }, [session.accessToken])

  const openChat = useCallback(
    async (chatId: string) => {
      setError('')
      setActiveChat(await getChat(session.accessToken, chatId))
    },
    [session.accessToken],
  )

  useEffect(() => {
    void (async () => {
      try {
        const nextChats = await refreshChats()
        if (nextChats[0]) await openChat(nextChats[0].id)
      } catch (loadError) {
        setError(
          loadError instanceof Error ? loadError.message : 'Falha ao carregar',
        )
      } finally {
        setLoading(false)
      }
    })()
  }, [openChat, refreshChats])

  const newChat = async () => {
    const chat = await createChat(session.accessToken)
    await refreshChats()
    await openChat(chat.id)
  }

  return (
    <main className="grid h-svh grid-cols-[280px_1fr] overflow-hidden bg-background">
      <aside className="flex min-h-0 flex-col border-r bg-muted/30">
        <div className="flex h-16 items-center gap-3 px-4">
          <div className="flex size-9 items-center justify-center rounded-xl bg-orange-500 text-white">
            <BotIcon className="size-5" />
          </div>
          <div className="min-w-0">
            <p className="truncate font-semibold">Banking Assistant</p>
            <Badge variant="secondary" className="mt-0.5 capitalize">
              {session.roles[0] ?? 'user'}
            </Badge>
          </div>
        </div>
        <Separator />
        <div className="p-3">
          <Button className="w-full justify-start gap-2" onClick={newChat}>
            <PlusIcon className="size-4" />
            Novo atendimento
          </Button>
        </div>
        <nav className="min-h-0 flex-1 space-y-1 overflow-y-auto px-3 pb-3">
          {loading && (
            <p className="px-2 py-4 text-sm text-muted-foreground">
              Carregando conversas...
            </p>
          )}
          {chats.map((chat) => (
            <Button
              key={chat.id}
              variant={activeChat?.id === chat.id ? 'secondary' : 'ghost'}
              className="w-full justify-start gap-2"
              onClick={() => openChat(chat.id)}
            >
              <MessageSquareIcon className="size-4" />
              <span className="truncate">
                Atendimento {chat.id.slice(0, 8)}
              </span>
            </Button>
          ))}
        </nav>
        <Separator />
        <div className="p-3">
          <Button
            variant="ghost"
            className="w-full justify-start gap-2"
            onClick={onLogout}
          >
            <LogOutIcon className="size-4" />
            Sair
          </Button>
        </div>
      </aside>
      <section className="min-w-0">
        {error ? (
          <div className="p-6 text-sm text-destructive">{error}</div>
        ) : activeChat ? (
          <ChatThread
            key={activeChat.id}
            session={session}
            chat={activeChat}
            onReload={() => openChat(activeChat.id)}
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <div className="text-center">
              <BotIcon className="mx-auto mb-4 size-10 text-orange-500" />
              <h1 className="text-xl font-semibold">Inicie um atendimento</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Crie uma conversa para falar com o agente.
              </p>
            </div>
          </div>
        )}
      </section>
    </main>
  )
}

function ChatThread({
  session,
  chat,
  onReload,
}: {
  session: Session
  chat: ChatDetail
  onReload: () => Promise<void>
}) {
  const [messages, setMessages] = useState<UiMessage[]>(() =>
    chat.messages.map((message) =>
      message.role === 'assistant'
        ? {
            id: message.id,
            role: message.role,
            content: message.content,
            createdAt: new Date(message.created_at),
            status: { type: 'complete', reason: 'stop' },
          }
        : {
            id: message.id,
            role: message.role,
            content: message.content,
            createdAt: new Date(message.created_at),
          },
    ),
  )
  const [isRunning, setIsRunning] = useState(false)

  const onNew = useCallback(
    async (message: AppendMessage) => {
      const content = message.content
        .filter((part) => part.type === 'text')
        .map((part) => part.text)
        .join('')
        .trim()

      if (!content || isRunning) return

      const userMessage: UiMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content,
        createdAt: new Date(),
      }
      const assistantId = crypto.randomUUID()
      setMessages((current) => [
        ...current,
        userMessage,
        {
          id: assistantId,
          role: 'assistant',
          content: '',
          createdAt: new Date(),
          status: { type: 'running' },
        },
      ])
      setIsRunning(true)

      try {
        await streamMessage(
          session.accessToken,
          chat.id,
          content,
          (event: AgentEvent) => {
            setMessages((current) =>
              current.map((item) => {
                if (item.id !== assistantId) return item

                if (event.type === 'chunk') {
                  return {
                    ...item,
                    content: item.content + (event.payload.content ?? ''),
                  }
                }

                if (event.type === 'completed') {
                  return {
                    ...item,
                    content: event.payload.content ?? item.content,
                    status: { type: 'complete', reason: 'stop' },
                  }
                }

                if (event.type === 'failed') {
                  return {
                    ...item,
                    status: {
                      type: 'incomplete',
                      reason: 'error',
                      error: event.payload.code ?? 'Falha no atendimento',
                    },
                  }
                }

                return item
              }),
            )
          },
        )
        await onReload()
      } catch (streamError) {
        const errorMessage =
          streamError instanceof Error
            ? streamError.message
            : 'Falha no atendimento'
        setMessages((current) =>
          current.map((item) =>
            item.id === assistantId
              ? {
                  ...item,
                  status: {
                    type: 'incomplete',
                    reason: 'error',
                    error: errorMessage,
                  },
                }
              : item,
          ),
        )
      } finally {
        setIsRunning(false)
      }
    },
    [chat.id, isRunning, onReload, session.accessToken],
  )

  const runtime = useExternalStoreRuntime({
    messages,
    isRunning,
    setMessages: (nextMessages) => setMessages([...nextMessages]),
    onNew,
    convertMessage: (message: UiMessage) =>
      message.role === 'assistant'
        ? {
            id: message.id,
            role: message.role,
            content: message.content,
            createdAt: message.createdAt,
            status: message.status,
          }
        : {
            id: message.id,
            role: message.role,
            content: message.content,
            createdAt: message.createdAt,
          },
  })

  const welcome = useMemo(
    () =>
      function Welcome() {
        return (
          <div className="mb-8 text-center">
            <BotIcon className="mx-auto mb-3 size-10 text-orange-500" />
            <h1 className="text-2xl font-semibold">Como posso ajudar?</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Consulte informações ou solicite uma operação bancária.
            </p>
          </div>
        )
      },
    [],
  )

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <Thread components={{ Welcome: welcome }} />
    </AssistantRuntimeProvider>
  )
}

export default App
