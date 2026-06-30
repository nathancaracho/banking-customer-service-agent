# Agents

O projeto `agents` contém workers que executam o `CustomerServiceAgent`, o agente de atendimento bancário.

## Arquitetura

~~~d2
direction: right

worker: AgentWorker {
  style.fill: "#e8f5e9"
}

agent: CustomerServiceAgent {
  style.fill: "#e3f2fd"
}

hitl: HumanInTheLoopMiddleware {
  style.fill: "#fff3e0"
}

identity: IdentityMiddleware {
  style.fill: "#fce4ec"
}

observability: ObservabilityMiddleware {
  style.fill: "#fffde7"
}

tools: Tools {
  get_balance: get_balance
  get_card_limit: get_card_limit
  execute_limit_update: execute_limit_update
  execute_pix: execute_pix
  retrieve_knowledge: retrieve_knowledge

  style.fill: "#e0f7fa"
}

worker -> agent: run(request)
agent -> hitl: execute_limit_update / execute_pix
agent -> identity: All protected tools
agent -> observability: All tools
agent -> tools
tools -> mcp_proxy: HTTP
tools -> vector_db: RAG

mcp_proxy: MCP Proxy
vector_db: Vector DB
~~~

## Componentes

### `CustomerServiceAgent`

Classe principal que orquestra o agente. Responsabilidades:

- Criar o agente LangChain com `create_agent()`
- Gerenciar fluxo HITL (Human-in-the-Loop)
- Retomar checkpoints de operações interrompidas
- Retornar `AgentOutcome` ao worker

```python
class CustomerServiceAgent:
    async def run(self, request: AgentRequest) -> AgentOutcome
```

### Tools

Ferramentas LangChain disponíveis para o agente:

| Tool | Descrição | Protegida? |
|---|---|---|
| `get_balance` | Consulta saldo da conta | Sim (`balance.read`) |
| `get_card_limit` | Consulta limite do cartão | Sim (`card_limit.read`) |
| `execute_limit_update` | Executa aumento de limite | Sim (`card_limit.read` + `card_limit.update`) |
| `execute_pix` | Executa transferência PIX | Sim (`balance.read` + `pix.transfer`) |
| `retrieve_knowledge` | Busca na base de conhecimento | Não |

### Middleware

#### Identity Middleware

Intercepta todas as chamadas a ferramentas protegidas e valida autorização:

```python
@wrap_tool_call
async def identity_middleware(request: ToolCallRequest, handler) -> ToolMessage:
    ctx: CustomerServiceContext = request.runtime.context
    # ... valida autorização via Identity ...
    return await handler(request)
```

 Usa `request.runtime.context` (padrão LangChain) para acessar `identity_client`, `subject`, `request_id` e `chat_id`.

#### HumanInTheLoop Middleware

Interrompe execução antes de operações financeiras que exigem confirmação:

```python
HumanInTheLoopMiddleware(interrupt_on={
    "execute_limit_update": True,
    "execute_pix": True,
})
```

Quando o LLM tenta chamar uma dessas tools, o middleware levanta `GraphInterrupt` com os detalhes da operação. O agente captura e retorna `AgentOutcome(requires_confirmation=True)`.

#### Observability Middleware

Registra métricas de duração e resultado de cada tool call via `record_llm_call()`.

## Fluxo de Execução

### Fluxo Normal (consulta)

1. `AgentWorker` recebe `AgentRequest` da fila
2. Chama `agent.run(request)`
3. `CustomerServiceAgent` cria agente LangChain com middleware
4. LLM decide qual tool usar
5. Identity middleware valida autorização
6. Tool executa e retorna resultado
7. Observability middleware registra métricas
8. Agente retorna `AgentOutcome(content="...")`
9. Worker publica chunks na reply queue

### Fluxo HITL (operação financeira)

1. LLM decide usar `execute_limit_update` ou `execute_pix`
2. `HumanInTheLoopMiddleware` intercepta e levanta `GraphInterrupt`
3. `CustomerServiceAgent` captura o interrupt
4. Retorna `AgentOutcome(requires_confirmation=True, tool_name="...", parameters={...})`
5. Worker cria checkpoint no PostgreSQL
6. Publica evento `confirmation_required`
7. Usuário confirma → nova request com `checkpoint_id`
8. `CustomerServiceAgent` lê checkpoint e executa a tool

### Fluxo de Checkpoint

1. `AgentRequest` contém `payload.checkpoint_id`
2. `CustomerServiceAgent._resume_from_checkpoint()` lê o checkpoint do PostgreSQL
3. Verifica status (`pending`)
4. Executa a tool correspondente (`execute_limit_update` ou `execute_pix`)
5. Retorna `AgentOutcome` com o resultado

## Modelos

### `AgentRequest`

```python
class AgentRequest(BaseModel):
    request_id: str
    chat_id: str
    subject: Subject
    timestamp: datetime
    payload: AgentRequestPayload
```

### `AgentOutcome`

```python
@dataclass(frozen=True)
class AgentOutcome:
    content: str
    requires_confirmation: bool = False
    tool_name: str | None = None
    parameters: dict | None = None
```

### `CustomerServiceContext`

Contexto passado via `agent.ainvoke(..., context=...)`:

```python
@dataclass(frozen=True)
class CustomerServiceContext:
    identity_client: object
    subject: Subject
    request_id: str
    chat_id: str
```

## Observabilidade

Métricas registradas por request:

- `agents.request.processing_duration_ms` — tempo total de processamento
- `agents.queue.depth` — profundidade da fila de requests
- Chamadas LLM via `record_llm_call()` (modelo, operação, duração, erro)
- Autorizações via `ToolMetrics.record_authorization()`

Traces com `trace_id`, `request_id`, `chat_id` propagados via OpenTelemetry.

## Configuração

Variáveis de ambiente (via `docker-compose.yml`):

| Variável | Default | Descrição |
|---|---|---|
| `AGENTS_RABBITMQ_URL` | — | URL do RabbitMQ |
| `AGENTS_REQUEST_QUEUE` | `agent.requests` | Fila de entrada |
| `AGENTS_REPLY_QUEUE` | `agent.replies` | Fila de resposta |
| `AGENTS_DATABASE_URL` | — | PostgreSQL connection string |
| `AGENTS_DATABASE_SCHEMA` | `agents` | Schema PostgreSQL |
| `AGENTS_IDENTITY_BASE_URL` | — | URL do Identity |
| `AGENTS_MCP_URL` | — | URL do MCP Proxy |
| `AGENTS_LITELLM_URL` | — | URL do LiteLLM |
| `AGENTS_LITELLM_MODEL` | `chat-default` | Modelo LLM |
| `AGENTS_EMBEDDING_MODEL` | — | Modelo de embedding |
| `AGENTS_CHROMA_URL` | — | URL do ChromaDB |
| `AGENTS_RETRIEVAL_RESULTS_LIMIT` | `3` | Limite de resultados RAG |
| `AGENTS_RESPONSE_CHUNK_SIZE` | `140` | Tamanho do chunk de resposta |

## Testes

```bash
uv run python -m pytest agents/tests/test_customer_service.py -v
```

Cinco cenários testados:

1. Resposta grounded com fontes da KB
2. Negação de acesso a saldo de terceiros
3. Interrupção HITL para aumento de limite
4. Interrupção HITL para transferência PIX
5. Tratamento de mensagem vazia
