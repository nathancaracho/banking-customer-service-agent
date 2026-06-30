# Backend API

O backend é a fronteira pública do sistema. Gerencia chats, memória, filas e entrega de respostas via SSE.

## Endpoints

### Chats

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/chats` | Criar novo chat |
| `POST` | `/api/chats/{chat_id}/messages` | Enviar mensagem |
| `POST` | `/api/chats/{chat_id}/confirm` | Confirmar operação |
| `DELETE` | `/api/chats/{chat_id}/requests/{request_id}` | Cancelar requisição |
| `GET` | `/api/chats/{chat_id}/stream` | Stream SSE |
| `GET` | `/api/chats/{chat_id}/messages` | Histórico de mensagens |

### Knowledge Base

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/knowledge/upload` | Upload de documento |
| `GET` | `/api/knowledge/documents` | Listar documentos |
| `GET` | `/api/knowledge/documents/{id}` | Detalhes do documento |
| `DELETE` | `/api/knowledge/documents/{id}` | Remover documento |
| `POST` | `/api/knowledge/search` | Buscar na KB |

## Fluxo de Mensagem

1. Frontend envia `POST /api/chats/{chat_id}/messages` com `{ content: "..." }`
2. Backend persiste a mensagem no PostgreSQL
3. Backend gera `request_id` (UUID v4)
4. Backend carrega memória:
   - Summary (se existir)
   - Janela de 20 mensagens recentes
5. Backend publica na `request_queue`
6. Backend inicia stream SSE para `GET /api/chats/{chat_id}/stream`
7. Frontend consome eventos SSE

## Server-Sent Events

```
event: chunk
data: {"request_id":"uuid","chat_id":"uuid","type":"chunk","sequence":1,"payload":{"content":"Olá"}}

event: confirmation_required
data: {"request_id":"uuid","chat_id":"uuid","type":"confirmation_required","payload":{"content":"...","checkpoint_id":"..."}}

event: completed
data: {"request_id":"uuid","chat_id":"uuid","type":"completed","payload":{"content":"Resposta final."}}

event: failed
data: {"request_id":"uuid","chat_id":"uuid","type":"failed","payload":{"code":"agent_failed"}}
```

## Memória

### Compressão

1. Backend monitora tokens do histórico
2. Se ultrapassar 4000 tokens:
   - Envia para LiteLLM com prompt de compressão
   - Persiste novo `summary` no PostgreSQL
   - Mensagens originais permanecem
3. Resumo incluído em `memory.summary` da próxima requisição

### Janela de Contexto

```python
{
    "summary": "Resumo das mensagens antigas",
    "recent_messages": [
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."}
    ]
}
```

## Knowledge Base

### Upload

- Aceita arquivos PDF, TXT, MD
- Tamanho máximo: 10MB
- Documento é chunked (256 chars, 50 overlap)
- Embeddings gerados via LiteLLM
- Armazenados no ChromaDB

### Estrutura

```
POST /api/knowledge/upload
Content-Type: multipart/form-data

file: documento.pdf
```

## Autenticação

- JWT via `Authorization: Bearer <token>`
- Validação no middleware `AuthMiddleware`
- Subject extraído do token e propagado

## Rate Limiting

- Por IP: 100 requests/minuto (configurável)
- Rate limit por chat para operações de confirmação

## Configuração

| Variável | Default | Descrição |
|---|---|---|
| `BACKEND_DATABASE_URL` | — | PostgreSQL connection string |
| `BACKEND_DATABASE_SCHEMA` | `backend` | Schema PostgreSQL |
| `BACKEND_JWT_SECRET` | — | Segredo JWT |
| `BACKEND_RABBITMQ_URL` | — | URL do RabbitMQ |
| `BACKEND_REQUEST_QUEUE` | `agent.requests` | Fila de entrada |
| `BACKEND_REPLY_QUEUE` | `agent.replies` | Fila de resposta |
| `BACKEND_STREAM_TIMEOUT_SECONDS` | `120` | Timeout do SSE |
| `BACKEND_RECENT_MESSAGES_LIMIT` | `20` | Janela de mensagens |
| `BACKEND_FRONTEND_ORIGIN` | `http://localhost:5173` | CORS origin |
| `BACKEND_LITELLM_URL` | `http://litellm:4000` | URL do LiteLLM |

## Observabilidade

- `chat.messages_sent_total` — mensagens enviadas
- `chat.processing_duration_seconds` — tempo total
- `chat.sse_connections_active` — conexões SSE ativas
- `chat.memory_compression_count` — compressões realizadas
