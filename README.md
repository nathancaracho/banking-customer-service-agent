# Banking Customer Service Agent

Assistente bancário seguro com RAG, MCP, autorização por identidade, memória conversacional, auditoria e streaming em tempo real.

## Arquitetura

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────────────────────────────┐
│ Frontend │────▶│ Backend  │────▶│ RabbitMQ │────▶│ Agents (LangChain)               │
│ (React)  │◀────│(FastAPI) │◀────│          │◀────│  └─ CustomerServiceAgent          │
└──────────┘ SSE └──────────┘     └──────────┘     │     └─ IdentityMiddleware         │
                           │                        │     └─ HumanInTheLoopMiddleware   │
                           │                        │     └─ ObservabilityMiddleware    │
                           ▼                        └──────────┬───────────┘            │
                    ┌──────────┐                              │           │              │
                    │PostgreSQL│◀─────────────────────────────┘           │              │
                    │ (3 schemas)                                        ▼              │
                    └──────────┘                              ┌──────────┐    ┌─────────▼──┐
                                                              │ Vector DB│    │ MCP Proxy  │
                                                              │ (Chroma) │    │            │
                                                              └──────────┘    └─────┬──────┘
                                                                                    │
                                                                                    ▼
                                                                             ┌─────────────┐
                                                                             │ Banking API │
                                                                             └─────────────┘
```

| Serviço | Porta | Descrição |
|---|---|---|
| Frontend | 5173 | Chat UI e painel admin |
| Backend | 8200 | API REST, SSE, gestão de chats |
| Agents | — | Workers com `CustomerServiceAgent` |
| Identity | 8100 | Autenticação e autorização |
| Banking API | 8300 | Core bancário fake (saldo, limite, PIX) |
| MCP Proxy | 8400 | Tool catalog e adaptação HTTP |
| LiteLLM | 4000 | Gateway de modelos LLM |
| PostgreSQL | 5432 | Persistência (3 schemas) |
| ChromaDB | 8000 | Base de conhecimento vetorial |
| RabbitMQ | 5672 | Filas de request/reply |
| SigNoz | 3301 | Traces, métricas e logs |

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) + Docker Compose v2
- [uv](https://docs.astral.sh/uv/) (gerenciador de dependências Python)
- [Node.js](https://nodejs.org/) 18+ (apenas para desenvolvimento local do frontend)
- Chave de API de um provedor LLM (Gemini, OpenAI, Anthropic, etc.)

## Início Rápido

### 1. Clonar e configurar

```bash
git clone <repo-url>
cd banking-customer-service-agent

# Criar arquivo de variáveis de ambiente
cp .env.example .env

# Editar .env com suas credenciais
# Obrigatório: BACKEND_JWT_SECRET, BACKEND_DEMO_PASSWORD, pelo menos 1 chave LLM
```

### 2. Subir infraestrutura

```bash
make up
# ou
docker compose up -d
```

### 3. Verificar saúde

```bash
make status
# ou
docker compose ps
```

### 4. Acessar

| Serviço | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API (Swagger) | http://localhost:8200/docs |
| Identity API (Swagger) | http://localhost:8100/docs |
| Banking API (Swagger) | http://localhost:8300/docs |
| MCP Proxy | http://localhost:8400/mcp |
| SigNoz | http://localhost:3301 |
| RabbitMQ Admin | http://localhost:15672 (guest/guest) |

## Exemplos de Uso via API

### Criar chat

```bash
curl -X POST http://localhost:8200/api/chats \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

### Enviar mensagem

```bash
curl -X POST http://localhost:8200/api/chats/<chat_id>/messages \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"content": "Qual o meu saldo?"}'
```

### Consumir SSE

```bash
curl -N http://localhost:8200/api/chats/<chat_id>/stream \
  -H "Authorization: Bearer <token>"
```

### Confirmar operação

```bash
curl -X POST http://localhost:8200/api/chats/<chat_id>/confirm \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"request_id": "<request_id>", "confirmed": true}'
```

### Upload de documento na KB

```bash
curl -X POST http://localhost:8200/api/knowledge/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@documento.pdf"
```

### Buscar na KB

```bash
curl -X POST http://localhost:8200/api/knowledge/search \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "taxa do consignado"}'
```

## Makefile

```bash
make help            # Ver todos os comandos
make up              # Subir todos os serviços
make down            # Parar todos os serviços
make build           # Rebuild imagens Docker
make restart         # Reiniciar serviços
make logs            # Logs de todos os serviços
make logs-agents     # Logs apenas do agents
make logs-backend    # Logs apenas do backend
make logs-identity   # Logs apenas do identity
make status          # Status dos serviços
make test            # Rodar todos os testes
make test-agents     # Testes do agents
make test-backend    # Testes do backend
make test-identity   # Testes do identity
make docs            # Servir documentação (http://localhost:8080)
make docs-build      # Build da documentação
make migrate         # Rodar migrations
make shell-pg        # Shell no PostgreSQL
make shell-pg-agents # Shell no schema agents
make shell-pg-backend # Shell no schema backend
make shell-pg-identity # Shell no schema identity
make deps            # Instalar dependências de todos os projetos
make env             # Copiar .env.example → .env
make clean           # Limpar volumes e caches
make open-backend    # Abrir Swagger do Backend
make open-identity   # Abrir Swagger do Identity
make open-banking    # Abrir Swagger da Banking API
make open-signoz     # Abrir SigNoz
make open-rabbitmq   # Abrir RabbitMQ Admin
```

## Variáveis de Ambiente

### Core (infraestrutura)

| Variável | Obrigatória | Default | Descrição |
|---|---|---|---|
| `POSTGRES_DB` | Não | `app` | Nome do banco de dados |
| `POSTGRES_USER` | Não | `app` | Usuário do PostgreSQL |
| `POSTGRES_PASSWORD` | Não | `app` | Senha do PostgreSQL |
| `POSTGRES_PORT` | Não | `5432` | Porta do PostgreSQL |
| `RABBITMQ_USER` | Não | `app` | Usuário do RabbitMQ |
| `RABBITMQ_PASSWORD` | Não | `app` | Senha do RabbitMQ |
| `RABBITMQ_VHOST` | Não | `app` | Virtual host do RabbitMQ |
| `RABBITMQ_PORT` | Não | `5672` | Porta AMQP do RabbitMQ |
| `RABBITMQ_MANAGEMENT_PORT` | Não | `15672` | Porta do management UI |
| `CHROMA_PORT` | Não | `8000` | Porta do ChromaDB |
| `LITELLM_PORT` | Não | `4000` | Porta do LiteLLM |
| `LITELLM_MASTER_KEY` | Sim | — | Chave mestra do LiteLLM |

### Backend

| Variável | Obrigatória | Default | Descrição |
|---|---|---|---|
| `BACKEND_JWT_SECRET` | **Sim** | — | Segredo para assinatura JWT |
| `BACKEND_JWT_ALGORITHM` | Não | `HS256` | Algoritmo JWT |
| `BACKEND_DEMO_PASSWORD` | **Sim** | — | Senha do usuário demo |
| `BACKEND_PORT` | Não | `8200` | Porta do backend |
| `BACKEND_DATABASE_URL` | Não* | — | URL de conexão PostgreSQL |
| `BACKEND_DATABASE_SCHEMA` | Não | `backend` | Schema PostgreSQL |
| `BACKEND_RABBITMQ_URL` | Não* | — | URL de conexão RabbitMQ |
| `BACKEND_REQUEST_QUEUE` | Não | `agent.requests` | Nome da fila de requests |
| `BACKEND_REPLY_QUEUE` | Não | `agent.replies` | Nome da fila de replies |
| `BACKEND_STREAM_TIMEOUT_SECONDS` | Não | `120` | Timeout do stream SSE |
| `BACKEND_RECENT_MESSAGES_LIMIT` | Não | `20` | Janela de mensagens recentes |
| `BACKEND_FRONTEND_ORIGIN` | Não | `http://localhost:5173` | CORS origin |
| `BACKEND_LITELLM_URL` | Não | `http://litellm:4000` | URL do LiteLLM |
| `BACKEND_LITELLM_MODEL` | Não | `openai/gpt-4o-mini` | Modelo para compressão de memória |
| `BACKEND_EMBEDDING_MODEL` | Não | `kb-embedding` | Modelo de embedding |
| `BACKEND_CHROMA_URL` | Não | `http://chroma:8000` | URL do ChromaDB |
| `BACKEND_CHROMA_COLLECTION` | Não | `banking_knowledge_base_v1` | Coleção da KB |
| `BACKEND_KB_MAX_FILE_SIZE_BYTES` | Não | `10485760` | Tamanho máx upload (10MB) |

*Default compilado no Dockerfile via docker-compose.yml

### Agents

| Variável | Obrigatória | Default | Descrição |
|---|---|---|---|
| `AGENTS_RABBITMQ_URL` | Não* | — | URL de conexão RabbitMQ |
| `AGENTS_REQUEST_QUEUE` | Não | `agent.requests` | Fila de entrada |
| `AGENTS_REPLY_QUEUE` | Não | `agent.replies` | Fila de resposta |
| `AGENTS_DATABASE_URL` | Não* | — | URL de conexão PostgreSQL |
| `AGENTS_DATABASE_SCHEMA` | Não | `agents` | Schema PostgreSQL |
| `AGENTS_IDENTITY_BASE_URL` | Não | `http://identity:8100` | URL do Identity |
| `AGENTS_IDENTITY_TIMEOUT_SECONDS` | Não | `10` | Timeout da autorização |
| `AGENTS_MCP_URL` | Não | `http://mcp-proxy:8400/mcp` | URL do MCP Proxy |
| `AGENTS_MCP_TIMEOUT_SECONDS` | Não | `20` | Timeout do MCP |
| `AGENTS_LITELLM_URL` | Não | `http://litellm:4000` | URL do LiteLLM |
| `AGENTS_LITELLM_MODEL` | Não | `chat-default` | Nome do modelo LLM |
| `AGENTS_EMBEDDING_MODEL` | Não | `kb-embedding` | Modelo de embedding |
| `AGENTS_CHROMA_URL` | Não | `http://chroma:8000` | URL do ChromaDB |
| `AGENTS_CHROMA_COLLECTION` | Não | `banking_knowledge_base_v1` | Coleção da KB |
| `AGENTS_CHROMA_TENANT` | Não | `default_tenant` | Tenant do ChromaDB |
| `AGENTS_CHROMA_DATABASE` | Não | `default_database` | Database do ChromaDB |
| `AGENTS_RETRIEVAL_RESULTS_LIMIT` | Não | `3` | Limite de resultados RAG |
| `AGENTS_RESPONSE_CHUNK_SIZE` | Não | `140` | Tamanho do chunk de resposta |

### Identity

| Variável | Obrigatória | Default | Descrição |
|---|---|---|---|
| `IDENTITY_PORT` | Não | `8100` | Porta do Identity |
| `IDENTITY_DATABASE_URL` | Não* | — | URL de conexão PostgreSQL |
| `IDENTITY_DATABASE_SCHEMA` | Não | `identity` | Schema PostgreSQL |

### Banking API

| Variável | Obrigatória | Default | Descrição |
|---|---|---|---|
| `BANKING_API_PORT` | Não | `8300` | Porta da Banking API |
| `BANKING_API_DATABASE_URL` | Não* | — | URL de conexão PostgreSQL |
| `BANKING_API_DATABASE_SCHEMA` | Não | `banking_api` | Schema PostgreSQL |

### MCP Proxy

| Variável | Obrigatória | Default | Descrição |
|---|---|---|---|
| `MCP_PORT` | Não | `8400` | Porta do MCP Proxy |
| `MCP_BANKING_API_BASE_URL` | Não | `http://banking-api:8300` | URL da Banking API |
| `MCP_REQUEST_TIMEOUT_SECONDS` | Não | `10` | Timeout de requests HTTP |

### Frontend

| Variável | Obrigatória | Default | Descrição |
|---|---|---|---|
| `FRONTEND_PORT` | Não | `5173` | Porta do frontend |
| `VITE_API_URL` | Não | `http://localhost:8200` | URL da API backend |

### LLM (LiteLLM)

| Variável | Obrigatória | Default | Descrição |
|---|---|---|---|
| `LITELLM_MASTER_KEY` | Sim | — | Chave mestra do LiteLLM |
| `GEMINI_API_KEY` | Não** | — | Chave API Google Gemini |
| `OPENAI_API_KEY` | Não** | — | Chave API OpenAI |
| `ANTHROPIC_API_KEY` | Não** | — | Chave API Anthropic |
| `OPENROUTER_API_KEY` | Não** | — | Chave API OpenRouter |
| `OLLAMA_API_BASE` | Não** | — | URL do Ollama local |

**Pelo menos uma chave de provedor LLM é obrigatória.

### Observability (SigNoz)

| Variável | Obrigatória | Default | Descrição |
|---|---|---|---|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Não | `http://localhost:4317` | Endpoint do OTEL Collector |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | Não | `grpc` | Protocolo OTEL |
| `OTEL_DEPLOYMENT_ENVIRONMENT` | Não | `local` | Ambiente de deploy |
| `OTEL_SDK_DISABLED` | Não | `false` | Desabilitar SDK OTEL |
| `SIGNOZ_UI_PORT` | Não | `3301` | Porta da UI do SigNoz |
| `SIGNOZ_OTLP_GRPC_PORT` | Não | `4317` | Porta gRPC do OTEL Collector |
| `SIGNOZ_OTLP_HTTP_PORT` | Não | `4318` | Porta HTTP do OTEL Collector |

## Fluxos

### Fluxo de Mensagem

1. Usuário envia mensagem via Frontend
2. Backend persiste e monta memória (resumo + 20 mensagens recentes)
3. Backend publica na `request_queue`
4. Agent Worker consome e executa o `CustomerServiceAgent`
5. Identity middleware valida autorização de cada tool call
6. Observability middleware registra métricas
7. Agent publica chunks na `reply_queue`
8. Backend consome e entrega via SSE ao Frontend

### Fluxo de Confirmação (HITL)

1. Usuário pede operação financeira (aumento de limite ou PIX)
2. LLM decide usar `execute_limit_update` ou `execute_pix`
3. `HumanInTheLoopMiddleware` interrompe antes da execução
4. Agent retorna `AgentOutcome(requires_confirmation=True)`
5. Worker cria checkpoint no PostgreSQL
6. Frontend exibe modal de confirmação
7. Usuário confirma → nova request com `checkpoint_id`
8. Worker retoma execução e retorna resultado

### Fluxo RAG

1. Pergunta do usuário é enviada ao agente
2. Tool `retrieve_knowledge` busca no ChromaDB
3. Embeddings comparados via similaridade
4. Top 3 documentos retornados com metadados
5. Agente gera resposta grounded com citações
6. Resposta nunca inventa informação sem fonte

## Desenvolvimento Local (sem Docker)

### Agents

```bash
cd agents
uv sync
uv run python -m pytest tests/ -v
```

### Backend

```bash
cd backend
uv sync
uv run uvicorn backend.main:app --reload --port 8200
```

### Identity

```bash
cd identity
uv sync
uv run uvicorn identity.main:app --reload --port 8100
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Testes

```bash
make test            # Todos os projetos
make test-agents     # Apenas agents (8 testes)
make test-backend    # Apenas backend
make test-identity   # Apenas identity

# Verbose
cd agents && uv run python -m pytest tests/ -v
```

### Cobertura de Testes (Agents)

| Teste | Cenário |
|---|---|
| `test_returns_grounded_answer_with_sources` | Resposta RAG com fontes |
| `test_denies_third_party_balance_access` | Negação de acesso a saldo de terceiro |
| `test_interrupts_for_credit_limit_update` | HITL para aumento de limite |
| `test_interrupts_for_pix_transfer` | HITL para PIX |
| `test_handles_empty_message` | Mensagem vazia |
| `test_configures_create_agent_with_domain_tools_and_middlewares` | Configuração do agente |
| `test_sends_chat_memory_to_agent_invocation` | Memória enviada ao agente |
| `test_chunks_response_with_fixed_width` | Chunking de resposta |

## Migrations

```bash
make migrate  # Todos os projetos

# Ou individualmente
cd agents && uv run alembic upgrade head
cd backend && uv run alembic upgrade head
cd identity && uv run alembic upgrade head
```

### Schemas PostgreSQL

| Schema | Serviço | Tabelas |
|---|---|---|
| `backend` | Backend | chats, messages, memory_summaries |
| `agents` | Agents | checkpoints |
| `identity` | Identity | users, roles, policies, authorization_audit |

## Observabilidade

### SigNoz

- **UI**: http://localhost:3301
- **OTEL Collector**: http://localhost:4317 (gRPC)

### Métricas

| Métrica | Componente | Descrição |
|---|---|---|
| `chat.messages_sent_total` | Backend | Mensagens enviadas |
| `chat.processing_duration_seconds` | Backend | Tempo total |
| `chat.sse_connections_active` | Backend | Conexões SSE ativas |
| `chat.memory_compression_count` | Backend | Compressões realizadas |
| `agents.request.processing_duration_ms` | Agents | Tempo de processamento |
| `agents.queue.depth` | Agents | Profundidade da fila |
| `rag.query_total` | Agents | Consultas RAG |
| `rag.query_duration_seconds` | Agents | Latência RAG |
| `identity.authorization.total` | Identity | Verificações de auth |

### Traces

Todos os componentes propagam `trace_id`, `request_id` e `chat_id` via OpenTelemetry.

## Troubleshooting

### Serviço não inicia

```bash
# Verificar logs do serviço específico
make logs-agents
make logs-backend
make logs-identity

# Verificar se dependências estão saudáveis
docker compose ps
```

### Erro de autenticação JWT

```bash
# Verificar se BACKEND_JWT_SECRET está definido no .env
grep BACKEND_JWT_SECRET .env

# Gerar novo segredo
openssl rand -hex 32
```

### LiteLLM não responde

```bash
# Verificar se a chave de API está configurada
grep GEMINI_API_KEY .litellm/.env
# ou
grep OPENAI_API_KEY .litellm/.env

# Testar conectividade
curl http://localhost:4000/health
```

### PostgreSQL recusa conexão

```bash
# Verificar se o container está rodando
docker compose ps postgres

# Verificar logs
docker compose logs postgres

# Testar conexão
docker compose exec postgres psql -U app -d app -c "SELECT 1"
```

### RabbitMQ não conecta

```bash
# Verificar status
docker compose ps rabbitmq

# Acessar management UI
open http://localhost:15672  # guest/guest
```

### Colisão de porta

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
```

### Limpar tudo e recomeçar

```bash
make clean    # Remove containers e volumes
make up       # Sobe novamente
make migrate  # Roda migrations
```

## Estrutura do Monorepo

```
banking-customer-service-agent/
├── agents/                  # Agent workers (Python/LangChain)
│   ├── agents/
│   │   ├── customer_service.py   # Agente principal (~286 linhas)
│   │   ├── middleware.py         # Identity + Observability middleware
│   │   ├── tools.py             # Tools LangChain (5 tools)
│   │   ├── worker.py            # Worker RabbitMQ
│   │   ├── config.py            # Settings
│   │   ├── models.py            # Modelos Pydantic
│   │   ├── knowledge.py         # RAG retriever (ChromaDB)
│   │   ├── database.py          # SQLAlchemy session
│   │   ├── repository.py        # Checkpoint CRUD
│   │   └── clients/
│   │       └── identity_client.py # Cliente HTTP do Identity
│   └── tests/
├── backend/                 # API Backend (Python/FastAPI)
│   ├── backend/
│   │   ├── app.py               # Rotas principais
│   │   ├── auth.py              # JWT auth middleware
│   │   ├── broker.py            # RabbitMQ publisher/consumer
│   │   ├── memory.py            # Compressão de memória (LiteLLM)
│   │   ├── knowledge/           # KB upload/query
│   │   │   ├── routes.py
│   │   │   ├── service.py
│   │   │   ├── repository.py
│   │   │   ├── chroma_client.py
│   │   │   ├── text_chunker.py
│   │   │   └── document_parser.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py
│   │   └── schemas.py
│   └── tests/
├── identity/                # Identity Service (Python/FastAPI)
│   ├── identity/
│   │   ├── app.py               # Rotas (register, login, authorize)
│   │   ├── authorization.py     # Engine de autorização
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py            # User, Role, Policy
│   │   ├── repository.py
│   │   └── schemas.py
│   └── tests/
├── banking_api/             # Banking API fake (Python)
├── mcp_proxy/               # MCP Proxy (Python/FastMCP)
├── frontend/                # Chat UI (React)
├── observability/           # SigNoz + OTEL collector
├── specs/                   # Arquitetura e ADRs
│   ├── architecture.md
│   ├── tech-stack.md
│   ├── features/
│   └── adrs/
├── docs/                    # Documentação MkDocs
├── .litellm/                # Config do LiteLLM
│   ├── config.yaml           # Modelos e rotas
│   └── .env                  # Chaves de API
├── docker-compose.yml       # Orquestração
├── Makefile                 # Comandos convenientes
├── .env.example             # Template de variáveis
└── README.md                # Este arquivo
```

## Licença

MIT
