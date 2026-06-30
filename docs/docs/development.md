# Development

Guia completo de desenvolvimento local.

## Pré-requisitos

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (gerenciador de dependências)
- Docker e Docker Compose v2
- Node.js 18+ (apenas para frontend)
- Chave de API de um provedor LLM (Gemini, OpenAI, etc.)

## Setup Rápido

```bash
# 1. Copiar variáveis de ambiente
cp .env.example .env

# 2. Editar .env com suas credenciais
#    Obrigatório: BACKEND_JWT_SECRET, BACKEND_DEMO_PASSWORD, pelo menos 1 chave LLM

# 3. Subir infraestrutura
make up

# 4. Verificar
make status
```

## Estrutura do Monorepo

```
banking-customer-service-agent/
├── agents/              # Agent workers (Python/LangChain)
│   ├── agents/          # Código fonte
│   │   ├── customer_service.py  # Agente principal
│   │   ├── middleware.py        # Identity + Observability
│   │   ├── tools.py            # Tools LangChain
│   │   ├── worker.py           # Worker RabbitMQ
│   │   ├── config.py           # Settings
│   │   ├── models.py           # Modelos Pydantic
│   │   └── knowledge.py        # RAG retriever
│   └── tests/
├── backend/             # API Backend (Python/FastAPI)
│   ├── backend/
│   │   ├── app.py              # Rotas principais
│   │   ├── auth.py             # JWT auth
│   │   ├── broker.py           # RabbitMQ
│   │   ├── memory.py           # Compressão de memória
│   │   └── knowledge/          # KB upload/query
│   └── tests/
├── identity/            # Identity Service (Python/FastAPI)
├── banking_api/         # Banking API fake
├── mcp_proxy/           # MCP Proxy
├── frontend/            # Chat UI (React)
├── observability/       # SigNoz
├── .litellm/            # Config do LiteLLM
│   ├── config.yaml      # Modelos
│   └── .env             # Chaves de API
└── docker-compose.yml
```

## Usando Cada Serviço

### PostgreSQL

Banco de dados compartilhado com 3 schemas:

```bash
# Shell no banco
docker compose exec postgres psql -U app -d app

# Listar schemas
\dn

# Ver tabelas do backend
SET search_path TO backend;
\dt

# Ver tabelas do agents
SET search_path TO agents;
\dt

# Ver tabelas do identity
SET search_path TO identity;
\dt
```

**Schemas:**

| Schema | Tabelas | Serviço |
|---|---|---|
| `backend` | chats, messages, memory_summaries | Backend |
| `agents` | checkpoints | Agents |
| `identity` | users, roles, policies, authorization_audit | Identity |

### RabbitMQ

Fila de mensagens entre Backend e Agents:

```bash
# Management UI
open http://localhost:15672  # guest/gest

# Filas padrão:
# - agent.requests  (backend → agents)
# - agent.replies   (agents → backend)
```

**Verificar filas:**
```bash
# Via CLI
docker compose exec rabbitmq rabbitmqctl list_queues -p app

# Via API
curl -u guest:guest http://localhost:15672/api/queues
```

### LiteLLM

Gateway de modelos LLM. Ver [LiteLLM — Configuração de Modelos](litellm.md) para guia completo.

```bash
# Health check
curl http://localhost:4000/health

# Listar modelos
curl http://localhost:4000/v1/models \
  -H "Authorization: Bearer sk-local-development"

# Testar chat
curl http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-local-development" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "chat-default",
    "messages": [{"role": "user", "content": "Olá!"}]
  }'
```

### ChromaDB

Banco vetorial para a base de conhecimento:

```bash
# Listar coleções
curl http://localhost:8000/api/v2/tenants/default_tenant/databases/default_database/collections

# Buscar documentos
curl -X POST http://localhost:8000/api/v2/tenants/default_tenant/databases/default_database/collections/banking_knowledge_base_v1/query \
  -H "Content-Type: application/json" \
  -d '{"query_embeddings": [[0.1, 0.2, ...]], "n_results": 3}'
```

### Identity

Serviço de autenticação e autorização:

```bash
# Swagger
open http://localhost:8100/docs

# Registrar usuário
curl -X POST http://localhost:8100/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "senha123"}'

# Login
curl -X POST http://localhost:8100/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "senha123"}'

# Verificar autorização
curl -X POST http://localhost:8100/v1/authorization/check \
  -H "Content-Type: application/json" \
  -d '{
    "subject": {"user_id": "usr_123", "roles": ["customer"]},
    "action": "balance.read",
    "resource": {"type": "customer_account", "owner_id": "usr_123"},
    "context": {"request_id": "req_1", "chat_id": "chat_1", "tool_name": "get_balance"}
  }'
```

### Backend

API principal do sistema:

```bash
# Swagger
open http://localhost:8200/docs

# Criar chat
curl -X POST http://localhost:8200/api/chats \
  -H "Authorization: Bearer <token>"

# Enviar mensagem
curl -X POST http://localhost:8200/api/chats/<chat_id>/messages \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"content": "Qual o meu saldo?"}'

# Consumir SSE
curl -N http://localhost:8200/api/chats/<chat_id>/stream \
  -H "Authorization: Bearer <token>"

# Upload de documento
curl -X POST http://localhost:8200/api/knowledge/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@documento.pdf"

# Buscar na KB
curl -X POST http://localhost:8200/api/knowledge/search \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "taxa do consignado"}'
```

### Banking API

API fake para desenvolvimento:

```bash
# Swagger
open http://localhost:8300/docs

# Health check
curl http://localhost:8300/health

# Saldo
curl http://localhost:8300/v1/customers/usr_123/balance

# Limite do cartão
curl http://localhost:8300/v1/customers/usr_123/card-limit

# Criar PIX
curl -X POST http://localhost:8300/v1/pix \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "usr_123", "destination_key": "pix@example.com", "amount": 100}'
```

### MCP Proxy

Proxy entre agents e Banking API:

```bash
# Listar tools disponíveis
curl http://localhost:8400/mcp/tools

# Health check
curl http://localhost:8400/health
```

### Frontend

Interface React:

```bash
cd frontend
npm install
npm run dev

# Acessar
open http://localhost:5173
```

## Agents — Guia Detalhado

### Arquitetura

```
AgentWorker → CustomerServiceAgent → create_agent()
                                        ├── HumanInTheLoopMiddleware
                                        ├── IdentityMiddleware
                                        └── ObservabilityMiddleware
                                    → Tools
                                        ├── get_balance
                                        ├── get_card_limit
                                        ├── execute_limit_update
                                        ├── execute_pix
                                        └── retrieve_knowledge
```

### Como o Agente Funciona

1. Worker consome mensagem da `request_queue`
2. `CustomerServiceAgent.run()` cria agente LangChain
3. LLM decide qual tool usar
4. Middleware de identidade valida autorização
5. Middleware HITL interrompe antes de operações financeiras
6. Tool executa e retorna resultado
7. Worker publica chunks na `reply_queue`

### Tools Protegidas

| Tool | Ações de Auth |
|---|---|
| `get_balance` | `balance.read` |
| `get_card_limit` | `card_limit.read` |
| `execute_limit_update` | `card_limit.read` + `card_limit.update` |
| `execute_pix` | `balance.read` + `pix.transfer` |
| `retrieve_knowledge` | *(não protegida)* |

### Fluxo HITL

1. Usuário: "Quero aumentar meu limite para R$ 15.000"
2. LLM chama `execute_limit_update`
3. `HumanInTheLoopMiddleware` interrompe
4. Agente retorna `AgentOutcome(requires_confirmation=True)`
5. Worker cria checkpoint
6. Frontend exibe modal de confirmação
7. Usuário confirma → nova request com `checkpoint_id`
8. Worker retoma e executa

### Testes

```bash
cd agents
uv run python -m pytest tests/ -v
```

**8 cenários:**

| Teste | Cenário |
|---|---|
| `test_returns_grounded_answer_with_sources` | Resposta RAG com fontes |
| `test_denies_third_party_balance_access` | Negação de acesso |
| `test_interrupts_for_credit_limit_update` | HITL aumento de limite |
| `test_interrupts_for_pix_transfer` | HITL PIX |
| `test_handles_empty_message` | Mensagem vazia |
| `test_configures_create_agent_with_domain_tools_and_middlewares` | Config do agente |
| `test_sends_chat_memory_to_agent_invocation` | Memória enviada |
| `test_chunks_response_with_fixed_width` | Chunking |

## Backend — Guia Detalhado

### Autenticação

```bash
# Login para obter token
curl -X POST http://localhost:8200/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@bank.com", "password": "sua-senha"}'

# Usar token em requests
curl http://localhost:8200/api/chats \
  -H "Authorization: Bearer <token>"
```

### Compressão de Memória

Quando o histórico ultrapassa 4000 tokens:

1. Backend envia para LiteLLM com prompt de compressão
2. LiteLLM gera resumo
3. Resumo salvo no PostgreSQL (`memory_summaries`)
4. Próxima request inclui `memory.summary`

### Knowledge Base

**Upload:**
```bash
curl -X POST http://localhost:8200/api/knowledge/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@documento.pdf"
```

Formatos aceitos: PDF, TXT, MD

**Processamento:**
1. Documento é chunked (256 chars, 50 overlap)
2. Embeddings gerados via LiteLLM (`kb-embedding`)
3. Armazenados no ChromaDB

**Busca:**
```bash
curl -X POST http://localhost:8200/api/knowledge/search \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "taxa do consignado"}'
```

## Identity — Guia Detalhado

### Usuários Padrão

| Email | Senha | Role |
|---|---|---|
| demo@bank.com | *(BACKEND_DEMO_PASSWORD)* | customer |

### Criar Usuário

```bash
curl -X POST http://localhost:8100/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "novo@bank.com",
    "password": "senha123",
    "roles": ["customer"]
  }'
```

### Políticas

Políticas definem quem pode fazer o quê:

```json
{
  "effect": "allow",
  "actions": ["balance.read"],
  "resource_types": ["customer_account"],
  "roles": ["customer"],
  "conditions": {"owner_match": true}
}
```

## Convenções de Código

### Python

- Estilo funcional, sem classes desnecessárias
- Helpers privados com prefixo `_`
- Configuração via variáveis de ambiente
- Migrations para toda mudança em models
- `frozen=True` em dataclasses

### Testes

- Unitários sem dependência de infra real
- Mocks e fakes para serviços externos
- Cenários negativos primeiro
- Não criar testes triviais

### Commits

```bash
make test  # Rodar testes antes de commitar
```

## Debugging

### Logs

```bash
make logs            # Todos os serviços
make logs-agents     # Apenas agents
make logs-backend    # Apenas backend
make logs-identity   # Apenas identity
```

### SigNoz

```bash
open http://localhost:3301
```

Traces, métricas e logs em tempo real.

### RabbitMQ

```bash
open http://localhost:15672  # guest/guest
```

Ver filas, mensagens e consumidores.

### PostgreSQL

```bash
make shell-pg           # Shell geral
make shell-pg-agents    # Schema agents
make shell-pg-backend   # Schema backend
make shell-pg-identity  # Schema identity
```

### Erros Comuns

| Erro | Causa | Solução |
|---|---|---|
| `Connection refused` | Serviço não está rodando | `make up` |
| `JWT decode error` | Segredo inválido | Verificar `BACKEND_JWT_SECRET` no .env |
| `LiteLLM timeout` | Modelo lento ou API com problema | Aumentar timeout ou trocar modelo |
| `ChromaDB not found` | Coleção não existe | Fazer upload de documento primeiro |
| `Port already in use` | Porta conflitante | Alterar porta no .env |
