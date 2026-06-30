# Feature Spec: Conversação e Experiência do Chat

## 1. Objetivo

Especificar o fluxo de conversação entre usuário e agente, incluindo gestão de sessão, continuidade de contexto, referências elípticas, streaming SSE, estados da conversa, fallback e tratamento de timeout/retry.

## 2. Escopo

- Criação e gerenciamento de chats (sessões)
- Envio de mensagens do usuário
- Recebimento de respostas via SSE
- Estados da conversa (`processing`, `chunk`, `confirmation_required`, `completed`, `failed`)
- Compressão de memória conversacional
- Timeout e retry
- Mensagens de fallback e erro amigáveis

## 3. Fora de Escopo

- Implementação do agente (prompt engineering, tool selection, RAG interno)
- Lógica de autorização (ver spec 04 e 06)
- Execução de operações bancárias (ver specs 03, 05)
- Auditoria detalhada (ver spec 07)

## 4. Atores Envolvidos

- **Usuário**: cliente, gerente ou admin que interage via chat
- **Frontend**: interface React com chat UI e consumo de SSE
- **Backend**: API FastAPI que gerencia chats, memória e filas

## 5. Dependências

- Frontend (chat UI, SSE client)
- Backend (Chat Service, Memory, Queue Gateway, SSE)
- LiteLLM (compressão de memória)
- Request Queue (publicação de mensagens)
- Reply Queue (consumo de eventos)
- PostgreSQL (schema `backend`: chats, mensagens)
- Observability (métricas e traces)

## 6. Premissas

- O backend é a fonte de verdade do chat e da memória
- O frontend não decide permissões
- O agente não gerencia o histórico oficial do chat
- A compressão de memória ocorre apenas quando o orçamento de tokens é excedido
- O chat completo permanece no PostgreSQL e não é indexado no banco vetorial

## 7. Fluxo Principal

### 7.1. Envio de Mensagem

1. Usuário digita mensagem no frontend
2. Frontend autentica requisição (token JWT)
3. Frontend envia `POST /api/chats/{chat_id}/messages` com `{ content: string }`
4. Backend persiste a mensagem no PostgreSQL
5. Backend gera `request_id` (UUID v4)
6. Backend carrega memória do chat:
   - Summary (se existir)
   - Janela de `N` mensagens recentes (configurável, default 20)
7. Backend publica na `request_queue`:
   ```json
   {
     "request_id": "uuid",
     "chat_id": "uuid",
     "auth_context": "token",
     "timestamp": "2026-06-28T12:00:00Z",
     "payload": {
       "message": { "role": "user", "content": "..." },
       "memory": {
         "summary": "resumo opcional",
         "recent_messages": []
       }
     }
   }
   ```
8. Backend inicia stream SSE para `GET /api/chats/{chat_id}/stream`
9. Frontend consome eventos SSE e renderiza conforme o tipo

### 7.2. Recebimento de Resposta (SSE)

O backend consome a `reply_queue` e emite eventos SSE:

```json
// processing
event: processing
data: {"request_id":"uuid","chat_id":"uuid","type":"processing","timestamp":"..."}

// chunk (múltiplos)
event: chunk
data: {"request_id":"uuid","chat_id":"uuid","type":"chunk","sequence":1,"payload":{"content":"Olá"}}

// chunk
event: chunk
data: {"request_id":"uuid","chat_id":"uuid","type":"chunk","sequence":2,"payload":{"content":", seu limite atual é de R$ 5.000"}}

// confirmation_required
event: confirmation_required
data: {"request_id":"uuid","chat_id":"uuid","type":"confirmation_required","payload":{"tool":"increase_credit_limit","args":{"new_limit":15000},"summary":"Aumentar limite para R$ 15.000?"}}

// completed (resposta final)
event: completed
data: {"request_id":"uuid","chat_id":"uuid","type":"completed","payload":{"content":"Limite aumentado para R$ 15.000 com sucesso."}}

// failed
event: failed
data: {"request_id":"uuid","chat_id":"uuid","type":"failed","payload":{"error":"unauthorized","message":"Você não tem permissão para esta operação."}}
```

### 7.3. Compressão de Memória

1. Backend monitora tokens do histórico (via LiteLLM tokenizer ou estimativa)
2. Se ultrapassar limite configurável (default 4000 tokens):
   - Envia histórico para LiteLLM com prompt de compressão
   - Persiste novo `summary` no PostgreSQL
   - Mensagens originais permanecem disponíveis (não são deletadas)
3. O resumo é incluído no campo `memory.summary` da próxima requisição

### 7.4. Confirmação de Operação

1. Usuário recebe `confirmation_required` no SSE
2. Frontend exibe modal de confirmação com resumo da operação
3. Usuário confirma ou cancela
4. Frontend envia `POST /api/chats/{chat_id}/confirm` com `{ request_id, confirmed: bool }`
5. Backend persiste confirmação e publica nova requisição na `request_queue` com `checkpoint_id`

## 8. Fluxos Alternativos

### 8.1. Chat Novo

- `chat_id` ausente ou `null`: backend cria novo chat, retorna `chat_id` na resposta
- Frontend redireciona para nova URL de chat

### 8.2. Cancelamento pelo Usuário

- Usuário clica "Cancelar" durante `processing`
- Frontend envia `DELETE /api/chats/{chat_id}/requests/{request_id}`
- Backend publica evento de cancelamento na `request_queue`
- Agente interrompe processamento (se possível) ou descarta resultado

### 8.3. Reconexão SSE

- Se a conexão SSE cair, frontend deve:
  1. Aguardar backoff exponencial (1s, 2s, 4s, max 30s)
  2. Reabrir conexão com `Last-Event-ID` (último sequence recebido)
  3. Backend reenviar eventos a partir do sequence

## 9. Fluxos de Erro

### 9.1. Timeout do Agente

- Backend configura TTL na `request_queue` (ex: 60s)
- Se o agente não responder em 60s:
  - Backend emite `event: failed` com `"message": "O agente demorou muito para responder. Tente novamente."`
  - Backend publica trace de erro
  - Chat permanece aberto para nova tentativa

### 9.2. Erro de Autenticação

- Backend valida JWT na entrada
- Se inválido: `401 Unauthorized`
- Frontend exibe "Sessão expirada. Faça login novamente."

### 9.3. Falha na Fila

- Se a `request_queue` estiver indisponível:
  - Backend retorna `503 Service Unavailable`
  - Frontend exibe "Serviço temporariamente indisponível. Tente novamente em alguns instantes."

### 9.4. Erro Interno do Agente

- Agente publica `event: failed` com payload `{ error: "internal_error", message: "..." }`
- Backend persiste erro no chat
- Frontend exibe mensagem amigável: "Ocorreu um erro ao processar sua solicitação."

## 10. Regras de Negócio

- RN01: O chat deve preservar a ordem cronológica das mensagens
- RN02: O resumo de memória nunca substitui o histórico completo
- RN03: Confirmações expiram após 5 minutos (configurável)
- RN04: Cancelamento de requisição em processamento não espera confirmação do agente
- RN05: Máximo de 10 chunks consecutivos sem resposta final (configurável)
- RN06: O frontend não toma decisões de autorização

## 11. Requisitos Funcionais

| ID | Descrição |
|----|-----------|
| RF01 | Criar novo chat |
| RF02 | Enviar mensagem em chat existente |
| RF03 | Confirmar operação |
| RF04 | Cancelar requisição em andamento |
| RF05 | Cancelar confirmação pendente |
| RF06 | Consumir stream SSE com reconexão |
| RF07 | Recuperar histórico de mensagens |
| RF08 | Comprimir memória quando limite de tokens for excedido |

## 12. Requisitos Não Funcionais

| ID | Descrição |
|----|-----------|
| RNF01 | Timeout de resposta do agente: 60s |
| RNF02 | Tamanho máximo da mensagem: 4096 caracteres |
| RNF03 | Reconexão SSE com backoff exponencial |
| RNF04 | O summary deve caber em 1024 tokens |
| RNF05 | Janela de mensagens recentes: 20 (configurável) |
| RNF06 | TTL da confirmação: 5 minutos |

## 13. Contratos / Interfaces

### POST /api/chats

```json
// Request
{}
// Response 201
{
  "chat_id": "uuid",
  "created_at": "2026-06-28T12:00:00Z"
}
```

### POST /api/chats/{chat_id}/messages

```json
// Request
{ "content": "Qual o meu limite?" }
// Response 202
{
  "request_id": "uuid",
  "status": "processing",
  "chat_id": "uuid"
}
```

### POST /api/chats/{chat_id}/confirm

```json
// Request
{ "request_id": "uuid", "confirmed": true }
// Response 202
{
  "request_id": "uuid",
  "status": "processing"
}
```

### GET /api/chats/{chat_id}/stream

Server-Sent Events conforme seção 7.2.

### DELETE /api/chats/{chat_id}/requests/{request_id}

```
Response 204 No Content
```

### GET /api/chats/{chat_id}/messages?limit=50&offset=0

```json
// Response 200
{
  "messages": [
    { "role": "user", "content": "...", "timestamp": "..." },
    { "role": "assistant", "content": "...", "timestamp": "..." }
  ],
  "total": 150
}
```

## 14. Modelo de Dados Necessário

### Schema `backend`

**chats**
| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | UUID PK | Identificador do chat |
| user_id | UUID FK | Dono do chat |
| title | VARCHAR(255) | Título opcional |
| status | ENUM('active','archived') | Estado do chat |
| created_at | TIMESTAMPTZ | Data de criação |
| updated_at | TIMESTAMPTZ | Última atualização |

**messages**
| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | UUID PK | Identificador da mensagem |
| chat_id | UUID FK | Chat relacionado |
| request_id | UUID | Request ID para correlação |
| role | ENUM('user','assistant','system') | Papel |
| content | TEXT | Conteúdo da mensagem |
| message_type | ENUM('text','confirmation','error') | Tipo |
| sequence | INT | Ordem no chat |
| created_at | TIMESTAMPTZ | Data de criação |

**memory_summaries**
| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | UUID PK | Identificador |
| chat_id | UUID FK | Chat relacionado |
| summary | TEXT | Resumo comprimido |
| compressed_at | TIMESTAMPTZ | Data da compressão |
| message_count_before | INT | Total de mensagens antes da compressão |

## 15. Eventos e Auditoria

| Evento | Trigger | Informação |
|--------|---------|------------|
| chat.created | Novo chat | chat_id, user_id |
| message.sent | Mensagem enviada | chat_id, request_id |
| message.failed | Erro do agente | chat_id, request_id, error |
| confirmation.pending | Confirmação solicitada | chat_id, request_id, tool, args |
| confirmation.resolved | Usuário confirmou/cancelou | chat_id, request_id, confirmed |
| request.cancelled | Usuário cancelou | chat_id, request_id |
| memory.compressed | Memória comprimida | chat_id, message_count, token_count |

## 16. Observabilidade

Métricas:
- `chat.messages_sent_total`: contador de mensagens enviadas
- `chat.processing_duration_seconds`: tempo entre envio e completed/failed
- `chat.sse_connections_active`: conexões SSE ativas no momento
- `chat.memory_compression_count`: total de compressões realizadas

Traces com `trace_id`, `request_id`, `chat_id` em todos os spans.

## 17. Segurança e Autorização

- O backend valida autenticação (JWT) em toda requisição
- O frontend obtém token via endpoint de auth (não especificado aqui)
- O `auth_context` nunca aparece em logs
- Confirmação de operação requer o mesmo `chat_id` e `request_id`

## 18. Critérios de Aceite

1. Mensagem é enviada e processada em menos de 60s
2. SSE entrega chunks em ordem e sem perda
3. Reconexão SSE recupera eventos perdidos
4. Confirmação é solicitada e processada corretamente
5. Cancelamento interrompe operação em andamento
6. Timeout gera mensagem de erro amigável
7. Memória é comprimida sem perder mensagens

## 19. Casos de Teste Sugeridos

| Caso | Cenário | Resultado Esperado |
|------|---------|--------------------|
| CT01 | Enviar mensagem com chat novo | Chat criado, mensagem processada |
| CT02 | Enviar mensagem com chat existente | Mensagem processada com contexto |
| CT03 | Reconexão SSE após queda | Eventos perdidos são reenviados |
| CT04 | Timeout do agente | Mensagem de erro amigável |
| CT05 | Confirmação aceita | Operação executada |
| CT06 | Confirmação cancelada | Operação não executada |
| CT07 | Confirmação expirada | Operação cancelada |
| CT08 | Cancelamento durante processing | Agente interrompido |
| CT09 | Compressão de memória ativada | Summary gerado, histórico preservado |
| CT10 | Token inválido | 401 Unauthorized |

## 20. Open Questions

1. Qual o mecanismo de autenticação exato do frontend? (cookie vs JWT bearer?)
2. Deve haver limite de chats ativos por usuário?
3. O chat deve ter suporte a anexos (imagens, documentos)?
4. Qual a política de retenção de chats arquivados?
