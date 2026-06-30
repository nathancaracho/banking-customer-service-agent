# Arquitetura

## Visão Geral

O monorepo contém seis aplicações:

| Projeto | Responsabilidade |
|---|---|
| `frontend` | Chat UI e telas administrativas |
| `backend` | API, chats, memória, SSE e filas |
| `agents` | Workers que executam o `CustomerServiceAgent` |
| `identity` | Usuários, roles e autorização |
| `banking_api` | Core bancário fake e stateful |
| `mcp_proxy` | Tools MCP e adaptação HTTP |

## Diagrama de Componentes

~~~d2
direction: right

frontend: Frontend

backend: Backend {
  auth: Auth
  chat: Chat Service
  memory: Memory
  queue: Queue Gateway
  stream: SSE

  auth -> chat
  chat -> memory: Build context
  chat -> queue: Agent request
  queue -> chat: Agent events
  chat -> stream

  style.fill: "#e3f2fd"
}

agents: Agents {
  worker: Agent Worker
  agent: CustomerServiceAgent

  worker -> agent

  style.fill: "#fff3e0"
}

identity: Identity {
  style.fill: "#fce4ec"
}

database: PostgreSQL
litellm: LiteLLM
request_queue: Request Queue
reply_queue: Reply Queue
vector_db: Vector DB
mcp_proxy: MCP Proxy
bank_apis: Banking API

frontend -> backend.auth
backend.chat <-> database
backend.memory -> litellm
backend.queue -> request_queue
reply_queue -> backend.queue
backend.stream -> frontend

agents.agent -> litellm
agents.agent -> vector_db: RAG
agents.agent -> identity: Authorize
agents.agent -> mcp_proxy: Execute tools
mcp_proxy -> bank_apis
bank_apis -> database

identity -> database
~~~

## Fluxos

### Fluxo de Mensagem

1. Frontend envia mensagem autenticada com `chat_id`
2. Backend persiste a mensagem e cria `request_id`
3. Backend carrega memória (resumo + mensagens recentes)
4. Backend publica na `request_queue`
5. Worker executa o agente e publica na `reply_queue`
6. Backend encaminha via SSE ao Frontend
7. Ao receber `completed`, backend persiste a resposta final

### Fluxo de Ferramenta

1. Agente seleciona ferramenta e argumentos
2. Middleware de identidade consulta o Identity
3. Identity valida contexto e operação
4. Se autorizada, agente executa via MCP Proxy
5. Se negada, MCP não é chamado
6. Se exigir confirmação (HITL), agente interrompe e retorna `confirmation_required`
7. Após confirmação do usuário, nova solicitação retoma via checkpoint

### Fluxo de Checkpoint

O worker não permanece bloqueado aguardando interação humana:

1. `HumanInTheLoopMiddleware` interrompe execução antes de `execute_limit_update` ou `execute_pix`
2. Worker cria checkpoint no PostgreSQL
3. Publica evento `confirmation_required`
4. Usuário confirma → nova requisição com `checkpoint_id`
5. Worker lê checkpoint e retoma execução

## Memória

### Memória do Chat (Backend)

Pertence ao backend. Contém:

- Resumo das mensagens antigas
- Janela de mensagens recentes (default: 20)
- Mensagem atual

O LiteLLM comprime o histórico quando ultrapassa o orçamento de tokens (default: 4000). O chat completo permanece no PostgreSQL.

### Checkpoint do Agente (Agents)

Pertence ao projeto `agents`. Contém estado técnico para retomar execução interrompida. Não substitui a memória do chat.

## Persistência

PostgreSQL com schemas separados:

| Schema | Conteúdo |
|---|---|
| `backend` | Chats, mensagens, resumos |
| `agents` | Checkpoints |
| `identity` | Usuários, roles, políticas, auditoria |

## Contratos das Filas

### Solicitação (`request_queue`)

```json
{
  "request_id": "uuid",
  "chat_id": "uuid",
  "subject": {
    "user_id": "usr_123",
    "roles": ["customer"]
  },
  "timestamp": "2026-06-30T12:00:00Z",
  "payload": {
    "message": { "role": "user", "content": "Qual é o meu limite?" },
    "memory": {
      "summary": "Resumo opcional",
      "recent_messages": []
    }
  }
}
```

### Evento (`reply_queue`)

```json
{
  "request_id": "uuid",
  "chat_id": "uuid",
  "type": "chunk",
  "sequence": 1,
  "payload": { "content": "Seu limite atual é de" }
}
```

Tipos de evento: `chunk`, `confirmation_required`, `completed`, `failed`.

## Decisões Arquiteturais

- Um único `CustomerServiceAgent` atende o domínio
- Streaming interno por chunks, não por token
- Backend controla chat e compressão de memória
- Identity obrigatório antes de ferramentas protegidas
- Banco vetorial armazena KB, não o chat
- PostgreSQL compartilhado, separado por schemas
- LiteLLM desacopla componentes dos provedores de modelo
