# Deployment

Guia completo de infraestrutura e deploy.

## Stack de Infraestrutura

| Serviço | Imagem | Porta | Health Check |
|---|---|---|---|
| PostgreSQL | `postgres:16-alpine` | 5432 | `pg_isready` |
| RabbitMQ | `rabbitmq:4-management-alpine` | 5672, 15672 | `rabbitmq-diagnostics ping` |
| ChromaDB | `chromadb/chroma:latest` | 8000 | — |
| LiteLLM | `docker.litellm.ai/berriai/litellm:main-latest` | 4000 | — |
| Identity | Custom | 8100 | — |
| Backend | Custom | 8200 | — |
| Banking API | Custom | 8300 | HTTP `/health` |
| MCP Proxy | Custom | 8400 | — |
| Agents | Custom | — | — |
| Frontend | Custom | 5173 | — |

## Início Rápido

```bash
# 1. Configurar
cp .env.example .env
# Editar .env (obrigatório: BACKEND_JWT_SECRET, BACKEND_DEMO_PASSWORD, 1 chave LLM)

# 2. Subir
make up

# 3. Verificar
make status

# 4. Acessar
open http://localhost:5173  # Frontend
```

## Serviços e Dependências

```d2
direction: right

postgres: PostgreSQL {
  style.fill: "#efebe9"
}

rabbitmq: RabbitMQ {
  style.fill: "#e3f2fd"
}

chroma: ChromaDB {
  style.fill: "#ede7f6"
}

litellm: LiteLLM {
  style.fill: "#f3e5f5"
}

identity: Identity
backend: Backend
agents: Agents
banking_api: Banking API
mcp_proxy: MCP Proxy
frontend: Frontend

backend -> postgres
backend -> rabbitmq
backend -> chroma
backend -> litellm

agents -> postgres
agents -> rabbitmq
agents -> chroma
agents -> litellm
agents -> identity
agents -> mcp_proxy

identity -> postgres

mcp_proxy -> banking_api
banking_api -> postgres

frontend -> backend
```

## Variáveis de Ambiente

### Core

| Variável | Obrigatória | Default | Descrição |
|---|---|---|---|
| `POSTGRES_DB` | Não | `app` | Nome do banco |
| `POSTGRES_USER` | Não | `app` | Usuário do banco |
| `POSTGRES_PASSWORD` | Não | `app` | Senha do banco |
| `POSTGRES_PORT` | Não | `5432` | Porta do PostgreSQL |
| `RABBITMQ_USER` | Não | `app` | Usuário RabbitMQ |
| `RABBITMQ_PASSWORD` | Não | `app` | Senha RabbitMQ |
| `RABBITMQ_VHOST` | Não | `app` | Virtual host |
| `RABBITMQ_PORT` | Não | `5672` | Porta AMQP |
| `RABBITMQ_MANAGEMENT_PORT` | Não | `15672` | Porta management UI |
| `CHROMA_PORT` | Não | `8000` | Porta ChromaDB |
| `LITELLM_PORT` | Não | `4000` | Porta LiteLLM |
| `LITELLM_MASTER_KEY` | Sim | — | Chave mestra LiteLLM |

### Backend

| Variável | Obrigatória | Default | Descrição |
|---|---|---|---|
| `BACKEND_JWT_SECRET` | **Sim** | — | Segredo JWT |
| `BACKEND_JWT_ALGORITHM` | Não | `HS256` | Algoritmo JWT |
| `BACKEND_DEMO_PASSWORD` | **Sim** | — | Senha do demo user |
| `BACKEND_PORT` | Não | `8200` | Porta do backend |
| `BACKEND_DATABASE_URL` | Não* | — | PostgreSQL URL |
| `BACKEND_DATABASE_SCHEMA` | Não | `backend` | Schema PostgreSQL |
| `BACKEND_RABBITMQ_URL` | Não* | — | RabbitMQ URL |
| `BACKEND_REQUEST_QUEUE` | Não | `agent.requests` | Fila de requests |
| `BACKEND_REPLY_QUEUE` | Não | `agent.replies` | Fila de replies |
| `BACKEND_STREAM_TIMEOUT_SECONDS` | Não | `120` | Timeout SSE |
| `BACKEND_RECENT_MESSAGES_LIMIT` | Não | `20` | Janela de mensagens |
| `BACKEND_FRONTEND_ORIGIN` | Não | `http://localhost:5173` | CORS origin |
| `BACKEND_LITELLM_URL` | Não | `http://litellm:4000` | URL LiteLLM |
| `BACKEND_LITELLM_MODEL` | Não | `openai/gpt-4o-mini` | Modelo para compressão |
| `BACKEND_EMBEDDING_MODEL` | Não | `kb-embedding` | Modelo de embedding |
| `BACKEND_CHROMA_URL` | Não | `http://chroma:8000` | URL ChromaDB |
| `BACKEND_CHROMA_COLLECTION` | Não | `banking_knowledge_base_v1` | Coleção KB |
| `BACKEND_KB_MAX_FILE_SIZE_BYTES` | Não | `10485760` | Tamanho máx upload |

### Agents

| Variável | Obrigatória | Default | Descrição |
|---|---|---|---|
| `AGENTS_RABBITMQ_URL` | Não* | — | RabbitMQ URL |
| `AGENTS_REQUEST_QUEUE` | Não | `agent.requests` | Fila de entrada |
| `AGENTS_REPLY_QUEUE` | Não | `agent.replies` | Fila de resposta |
| `AGENTS_DATABASE_URL` | Não* | — | PostgreSQL URL |
| `AGENTS_DATABASE_SCHEMA` | Não | `agents` | Schema PostgreSQL |
| `AGENTS_IDENTITY_BASE_URL` | Não | `http://identity:8100` | URL Identity |
| `AGENTS_IDENTITY_TIMEOUT_SECONDS` | Não | `10` | Timeout auth |
| `AGENTS_MCP_URL` | Não | `http://mcp-proxy:8400/mcp` | URL MCP Proxy |
| `AGENTS_MCP_TIMEOUT_SECONDS` | Não | `20` | Timeout MCP |
| `AGENTS_LITELLM_URL` | Não | `http://litellm:4000` | URL LiteLLM |
| `AGENTS_LITELLM_MODEL` | Não | `chat-default` | Modelo LLM |
| `AGENTS_EMBEDDING_MODEL` | Não | `kb-embedding` | Modelo embedding |
| `AGENTS_CHROMA_URL` | Não | `http://chroma:8000` | URL ChromaDB |
| `AGENTS_CHROMA_COLLECTION` | Não | `banking_knowledge_base_v1` | Coleção KB |
| `AGENTS_CHROMA_TENANT` | Não | `default_tenant` | Tenant ChromaDB |
| `AGENTS_CHROMA_DATABASE` | Não | `default_database` | Database ChromaDB |
| `AGENTS_RETRIEVAL_RESULTS_LIMIT` | Não | `3` | Limite RAG |
| `AGENTS_RESPONSE_CHUNK_SIZE` | Não | `140` | Tamanho chunk |

### Identity

| Variável | Obrigatória | Default | Descrição |
|---|---|---|---|
| `IDENTITY_PORT` | Não | `8100` | Porta Identity |
| `IDENTITY_DATABASE_URL` | Não* | — | PostgreSQL URL |
| `IDENTITY_DATABASE_SCHEMA` | Não | `identity` | Schema PostgreSQL |

### Banking API

| Variável | Obrigatória | Default | Descrição |
|---|---|---|---|
| `BANKING_API_PORT` | Não | `8300` | Porta Banking API |
| `BANKING_API_DATABASE_URL` | Não* | — | PostgreSQL URL |
| `BANKING_API_DATABASE_SCHEMA` | Não | `banking_api` | Schema PostgreSQL |

### MCP Proxy

| Variável | Obrigatória | Default | Descrição |
|---|---|---|---|
| `MCP_PORT` | Não | `8400` | Porta MCP Proxy |
| `MCP_BANKING_API_BASE_URL` | Não | `http://banking-api:8300` | URL Banking API |
| `MCP_REQUEST_TIMEOUT_SECONDS` | Não | `10` | Timeout HTTP |

### Frontend

| Variável | Obrigatória | Default | Descrição |
|---|---|---|---|
| `FRONTEND_PORT` | Não | `5173` | Porta frontend |
| `VITE_API_URL` | Não | `http://localhost:8200` | URL API backend |

### LLM (LiteLLM)

| Variável | Obrigatória | Default | Descrição |
|---|---|---|---|
| `LITELLM_MASTER_KEY` | Sim | — | Chave mestra LiteLLM |
| `GEMINI_API_KEY` | Não** | — | Chave Gemini |
| `OPENAI_API_KEY` | Não** | — | Chave OpenAI |
| `ANTHROPIC_API_KEY` | Não** | — | Chave Anthropic |
| `OPENROUTER_API_KEY` | Não** | — | Chave OpenRouter |
| `OLLAMA_API_BASE` | Não** | — | URL Ollama |

### Observability (SigNoz)

| Variável | Obrigatória | Default | Descrição |
|---|---|---|---|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Não | `http://localhost:4317` | Endpoint OTEL |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | Não | `grpc` | Protocolo |
| `OTEL_DEPLOYMENT_ENVIRONMENT` | Não | `local` | Ambiente |

## Observabilidade

### SigNoz

Stack completa via `observability/docker-compose.signoz.yaml`:

- **SigNoz UI**: http://localhost:3301
- **OTEL Collector**: http://localhost:4317 (gRPC)
- **ClickHouse**: armazenamento
- **Query Service**: API do SigNoz

### Métricas

| Métrica | Componente |
|---|---|
| `chat.messages_sent_total` | Backend |
| `chat.processing_duration_seconds` | Backend |
| `chat.sse_connections_active` | Backend |
| `chat.memory_compression_count` | Backend |
| `agents.request.processing_duration_ms` | Agents |
| `agents.queue.depth` | Agents |
| `rag.query_total` | Agents |
| `identity.authorization.total` | Identity |

## Persistência

### Volumes Docker

| Volume | Serviço | Dados |
|---|---|---|
| `postgres-data` | PostgreSQL | Todas as tabelas |
| `rabbitmq-data` | RabbitMQ | Filas e mensagens |
| `chroma-data` | ChromaDB | Embeddings e documentos |

### Schemas PostgreSQL

| Schema | Serviço | Tabelas Principais |
|---|---|---|
| `backend` | Backend | chats, messages, memory_summaries |
| `agents` | Agents | checkpoints |
| `identity` | Identity | users, roles, policies, authorization_audit |

## Health Checks

```bash
# Verificar todos
docker compose ps

# Verificar individualmente
curl http://localhost:8200/docs       # Backend
curl http://localhost:8100/docs       # Identity
curl http://localhost:8300/health     # Banking API
curl http://localhost:4000/health     # LiteLLM
curl http://localhost:8000/api/v2/heartbeat  # ChromaDB
```

## Gerenciamento

### Parar

```bash
make down        # Parar containers
make clean       # Parar e remover volumes
```

### Rebuild

```bash
make build       # Rebuild todas as imagens
make restart     # Reiniciar todos os serviços
```

### Logs

```bash
make logs            # Todos
make logs-agents     # Apenas agents
make logs-backend    # Apenas backend
make logs-identity   # Apenas identity
```

### Colisão de Portas

Se uma porta já está em uso, altere no `.env`:

```bash
POSTGRES_PORT=5433
RABBITMQ_PORT=5673
CHROMA_PORT=8001
LITELLM_PORT=4001
IDENTITY_PORT=8101
BACKEND_PORT=8201
BANKING_API_PORT=8301
MCP_PORT=8401
FRONTEND_PORT=5174
SIGNOZ_UI_PORT=3302
```

### Ambiente de Produção

Para produçao, considere:

1. **Senhas**: Usar senhas fortes, nunca defaults
2. **JWT**: Usar RS256 com chaves assimétricas
3. **TLS**: Termination TLS no reverse proxy
4. **Backup**: Backup regular do PostgreSQL
5. **Monitoramento**: Alertas no SigNoz
6. **Escalabilidade**: Workers independently scalable
7. **Redis**: Substituir InMemorySaver por Redis/PgSaver para HITL em produção
