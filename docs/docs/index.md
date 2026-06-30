~~~d2
direction: right

frontend: Frontend {
  style.fill: "#e8f5e9"
}

backend: Backend {
  auth: Auth
  chat: Chat Service
  memory: Memory
  knowledge: Knowledge API

  auth -> chat
  chat -> memory: Build context
  chat -> knowledge: Upload/query docs

  style.fill: "#e3f2fd"
}

agents: Agents {
  worker: Agent Worker
  customer_service: Customer Service Agent
  middleware: Identity Middleware
  hitl: HITL Middleware

  worker -> customer_service
  customer_service -> hitl: execute_limit_update / execute_pix
  customer_service -> middleware: All protected tools
  middleware -> customer_service: Authorized

  style.fill: "#fff3e0"
}

identity: Identity {
  style.fill: "#fce4ec"
}

request_queue: Request Queue
reply_queue: Reply Queue

litellm: LiteLLM {
  style.fill: "#f3e5f5"
}

mcp_proxy: MCP Proxy {
  tools: Tool Catalog
  bank_client: Bank API Client

  tools -> bank_client
  style.fill: "#e0f7fa"
}

bank_apis: Banking API {
  style.fill: "#f1f8e9"
}

database: PostgreSQL {
  style.fill: "#efebe9"
}

vector_db: Vector DB {
  style.fill: "#ede7f6"
}

observability: Observability {
  style.fill: "#fffde7"
}

frontend -> backend.auth: HTTPS
backend.auth -> backend.chat: Authenticated subject

backend.chat -> request_queue: Publish
request_queue -> agents.worker: Consume

agents.worker -> reply_queue: Publish chunks
reply_queue -> backend.chat: Consume

backend.chat -> database: Chats & memory
backend.memory -> litellm: Compress memory

agents.customer_service -> database: Checkpoints
identity -> database: Users & roles

agents.customer_service -> litellm: LLM calls
agents.customer_service -> vector_db: RAG retrieval
agents.middleware -> identity: Authorize tool call
agents.middleware -> mcp_proxy.tools: Execute when allowed

mcp_proxy.bank_client -> bank_apis: HTTP
bank_apis -> database: Banking state

backend -> observability
agents -> observability
mcp_proxy -> observability
identity -> observability
~~~

# Banking Customer Service Agent

Sistema de atendimento bancário com agente de IA que responde perguntas, consulta uma base de conhecimento e executa operações autorizadas.

## Componentes Principais

| Componente | Porta | Descrição |
|---|---|---|
| **Frontend** | 5173 | Chat UI e painel administrativo |
| **Backend** | 8200 | API REST, SSE, gestão de chats e memória |
| **Agents** | — | Workers que executam o `CustomerServiceAgent` |
| **Identity** | 8100 | Autenticação, usuários e autorização |
| **Banking API** | 8300 | Core bancário fake (saldo, limite, PIX) |
| **MCP Proxy** | 8400 | Tool catalog e adaptação HTTP |
| **LiteLLM** | 4000 | Gateway de modelos LLM |
| **PostgreSQL** | 5432 | Persistência (backend, agents, identity schemas) |
| **Vector DB** | 8000 | ChromaDB — base de conhecimento |
| **RabbitMQ** | 5672 | Filas de solicitação e resposta |

## Fluxo Resumido

1. Usuário envia mensagem via Frontend
2. Backend persiste, monta memória e publica na `request_queue`
3. Agent Worker consome e executa o `CustomerServiceAgent`
4. Middleware de identidade autoriza tool calls antes da execução
5. Agent publica chunks na `reply_queue`
6. Backend consome e entrega via SSE ao Frontend

## Links Rápidos

- [Arquitetura completa](architecture.md)
- [Sistema de Agents](agents.md)
- [API Backend](backend.md)
- [Identity & Autorização](identity.md)
- [Deploy e Infraestrutura](deployment.md)
- [Guia de Desenvolvimento](development.md)
