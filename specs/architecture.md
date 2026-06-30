# Arquitetura do sistema

Referências complementares:

- [Stack técnica](tech-stack.md)
- [ADR 001 — Agent middleware](adrs/001-agent-middleware.md)
- [ADR 002 — Chat memory in backend](adrs/002-chat-memory-in-backend.md)
- [ADR 003 — Identity before tool call](adrs/003-identity-before-tool-call.md)

## 1. Visão geral

O sistema fornece um agente de atendimento bancário capaz de responder perguntas, consultar uma base de conhecimento e executar operações autorizadas.

O monorepo contém seis aplicações:

- `frontend`: chat e telas administrativas;
- `backend`: API, chats, memória, SSE e integração com as filas;
- `agents`: workers que executam o `CustomerServiceAgent`;
- `identity`: usuários, roles e autorização de ferramentas;
- `banking_api`: core bancário fake e stateful para desenvolvimento local;
- `mcp_proxy`: tools MCP e adaptação HTTP para a Banking API.

O backend publica solicitações em uma fila. Os workers processam essas solicitações e publicam a resposta em chunks. O backend consome os chunks e os envia ao frontend por Server-Sent Events (SSE).

Funcionalidades com domínio próprio são organizadas em slices verticais dentro
do projeto. A gestão da base de conhecimento fica em `backend/backend/knowledge/`,
reunindo rotas, schemas, serviço, persistência, models e adapters externos.

## 2. Diagrama

```d2
direction: right

frontend: Frontend

backend: Backend {
  auth: Auth
  services: Services
}

agents: Agents {
  customer_service: Customer Service Agent
  authorization_middleware: Authorization Middleware

  customer_service -> authorization_middleware: Tool intent
}

request_queue: Request Queue
reply_queue: Reply Queue

litellm: LiteLLM
identity: Identity
mcp_proxy: MCP Proxy {
  tools: Tool Catalog
  bank_client: Bank API Client

  tools -> bank_client
}
bank_apis: Banking API (fake)
database: PostgreSQL
vector_db: Vector Database
observability: Observability

frontend -> backend.auth: HTTPS
backend.auth -> backend.services: Authenticated subject
backend.services -> frontend: SSE

backend.services -> request_queue: Publish
request_queue -> agents.customer_service: Consume

agents.customer_service -> reply_queue: Publish chunks
reply_queue -> backend.services: Consume

backend.services -> database: Chats and memory
backend.services -> litellm: Compress memory
agents.customer_service -> database: Checkpoint
identity -> database: Users and roles

agents.customer_service -> litellm
agents.customer_service -> vector_db: Retrieve
agents.authorization_middleware -> identity: Authorize tool call
agents.authorization_middleware -> mcp_proxy.tools: Execute when allowed
mcp_proxy.bank_client -> bank_apis: HTTPS
bank_apis -> database: Banking state

backend -> observability
agents -> observability
mcp_proxy -> observability
```

## 3. Componentes

### Frontend

Responsável por:

- autenticação por meio do backend;
- envio de mensagens;
- consumo do stream SSE;
- renderização dos estados `processing`, `chunk`, `confirmation_required`, `completed` e `failed`;
- interface administrativa para usuários e roles.

O frontend não decide permissões. Toda alteração administrativa é validada pelo backend e pelo Identity.

### Backend

É a fronteira pública e a fonte de verdade dos chats. Responsável por:

- receber requisições autenticadas e delegar a validação do contexto ao Identity;
- criar e gerenciar chats;
- persistir mensagens e respostas finais;
- montar e comprimir a memória conversacional;
- publicar solicitações na `request_queue`;
- consumir a `reply_queue` e encaminhar os eventos por SSE;
- tratar timeout, cancelamento e respostas atrasadas;
- expor as APIs administrativas.

```d2
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
}

database: PostgreSQL
litellm: LiteLLM
request_queue: Request Queue
reply_queue: Reply Queue

frontend -> backend.auth
backend.chat <-> database
backend.memory -> litellm: Compress
backend.queue -> request_queue
reply_queue -> backend.queue
backend.stream -> frontend
```

### Agents

O projeto contém workers independentes que executam o `CustomerServiceAgent`. O agente:

- recebe do backend a mensagem e a memória necessária;
- consulta a base de conhecimento;
- seleciona ferramentas;
- aplica middleware para consultar o Identity antes de qualquer tool protegida;
- executa ferramentas autorizadas pelo MCP;
- utiliza o LiteLLM como gateway de modelos;
- publica chunks e eventos na `reply_queue`;
- persiste checkpoints quando uma execução precisa ser retomada.

O agente não gerencia o histórico oficial do chat.

### Identity

Responsável por:

- validar o contexto de autenticação;
- identificar o usuário e suas roles;
- autorizar ou negar cada operação;
- responder às decisões consumidas pelo middleware do agente;
- manter usuários, roles e políticas;
- registrar decisões de autorização para auditoria.

Uma autorização considera o usuário, a role, a ferramenta, a ação, o recurso e os parâmetros da operação. O MCP só deve ser chamado após uma decisão positiva.

### Infraestrutura

- `LiteLLM`: abstração de modelos, fallback, métricas de uso e suporte a modelos locais ou mocks.
- `MCP`: ferramentas de consulta, operação bancária e operação crítica.
- `MCP Proxy`: servidor FastMCP que traduz tools autorizadas para a Banking API.
- `Banking API`: API fake stateful para perfil, saldo, limite e PIX.
- `PostgreSQL`: chats, mensagens, checkpoints, usuários, roles e auditoria.
- `Vector Database`: documentos e embeddings da base de conhecimento.
- `Observability`: logs, métricas e traces do backend e dos workers.

## 4. Fluxos

### Mensagem

1. O frontend envia uma mensagem autenticada com o `chat_id`.
2. O backend persiste a mensagem e cria um `request_id`.
3. O backend carrega a memória do chat e a comprime quando necessário.
4. O backend publica a mensagem, o resumo e as mensagens recentes na `request_queue`.
5. Um worker executa o agente e publica eventos na `reply_queue`.
6. O backend encaminha os eventos ao frontend por SSE.
7. Ao receber `completed`, o backend persiste a resposta final.

### Ferramenta

1. O agente seleciona a ferramenta e seus argumentos.
2. O middleware do agente envia a intenção de tool call ao Identity.
3. O Identity valida o contexto de autenticação e a operação solicitada.
4. Se autorizada, o agente executa a ferramenta pelo MCP.
5. Se negada, o MCP não é chamado.
6. Se exigir confirmação, o agente salva o checkpoint, publica `confirmation_required` e encerra a execução atual.
7. Após a confirmação do usuário, uma nova solicitação retoma o checkpoint.

O worker não permanece bloqueado enquanto aguarda interação humana.

## 5. Memória

Existem dois estados distintos:

### Memória do chat

Pertence ao backend e contém mensagens, respostas finais, confirmações e um resumo opcional.

O contexto enviado ao agente é formado por:

- resumo das mensagens antigas;
- janela de mensagens recentes;
- mensagem atual.

Quando o histórico ultrapassa o orçamento de tokens, o backend usa o LiteLLM para atualizar o resumo. O chat completo continua persistido no PostgreSQL e não é indexado no banco vetorial.

### Checkpoint do agente

Pertence ao projeto `agents` e contém o estado técnico necessário para retomar uma execução. Não substitui a memória do chat.

## 6. Contratos das filas

### Solicitação do agente

```json
{
  "request_id": "uuid",
  "chat_id": "uuid",
  "auth_context": "token",
  "timestamp": "2026-06-28T12:00:00Z",
  "payload": {
    "message": {
      "role": "user",
      "content": "Qual é o meu limite?"
    },
    "memory": {
      "summary": "O cliente consultou seu saldo anteriormente.",
      "recent_messages": []
    }
  }
}
```

`summary` pode ser `null` enquanto o histórico couber no orçamento de contexto. O `auth_context` não deve aparecer em logs.

### Evento do agente

```json
{
  "request_id": "uuid",
  "chat_id": "uuid",
  "type": "chunk",
  "sequence": 3,
  "timestamp": "2026-06-28T12:00:01Z",
  "payload": {
    "content": "Seu limite atual é de"
  }
}
```

Os eventos podem ser `chunk`, `confirmation_required`, `completed` ou `failed`. O campo numérico `sequence`, iniciado em `1`, informa a ordem dos chunks.

## 7. Persistência

Uma instância PostgreSQL é separada logicamente por schemas:

- `backend`: chats, mensagens e resumos;
- `agents`: checkpoints;
- `identity`: usuários, roles, políticas e auditoria.

## 8. Requisitos transversais

### Segurança

- Todo tráfego externo utiliza HTTPS.
- Tokens não são registrados em logs.
- O backend valida a autenticação na entrada.
- O Identity autoriza operações protegidas.
- Operações críticas exigem confirmação explícita e podem exigir autenticação adicional.
- Autorizações e operações executadas geram auditoria.

### Observabilidade

Backend e workers propagam `trace_id`, `request_id` e `chat_id`.

As principais métricas são:

- conexões SSE ativas;
- profundidade e tempo de espera das filas;
- tempo total e tempo até o primeiro chunk;
- duração de chamadas ao modelo e ferramentas;
- erros, timeouts, tokens e custo por modelo.

### Escalabilidade

- Backend, workers e Identity escalam de forma independente.
- O backend escala conforme conexões e requisições.
- Os workers escalam conforme profundidade da fila e tempo de processamento.
- Cada worker processa múltiplas solicitações dentro do seu limite de concorrência.
- A fila absorve picos e aplica backpressure.

## 9. Decisões

- Um único `CustomerServiceAgent` atende o domínio.
- O agente é executado por workers assíncronos.
- O streaming interno ocorre por chunks, não por token.
- O backend controla o chat e sua compressão.
- O agente persiste apenas checkpoints.
- O Identity é obrigatório antes de ferramentas protegidas.
- O banco vetorial armazena a base de conhecimento, não o chat.
- PostgreSQL é compartilhado fisicamente e separado por schemas.
- LiteLLM desacopla os componentes dos provedores de modelo.
