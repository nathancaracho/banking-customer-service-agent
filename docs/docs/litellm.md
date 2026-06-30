# LiteLLM — Configuração de Modelos

LiteLLM é o gateway de modelos LLM do projeto. Abstrai provedores (Gemini, OpenAI, Anthropic, etc.) atrás de uma API OpenAI-compatível.

## Como Funciona

```
Agents/Backend → LiteLLM (porta 4000) → Provedor (Gemini, OpenAI, etc.)
```

- **Endpoint**: `http://litellm:4000/v1` (dentro do Docker) ou `http://localhost:4000/v1` (fora)
- **Auth**: `Authorization: Bearer <LITELLM_MASTER_KEY>`
- **Compatível com**: API OpenAI (Chat Completions, Embeddings)

## Arquivos de Configuração

```
.litellm/
├── config.yaml    # Modelos e rotas
└── .env           # Chaves de API dos provedores
```

## Configuração Atual

### `.litellm/config.yaml`

```yaml
model_list:
  # Modelo principal para chat (agents + backend)
  - model_name: chat-default
    litellm_params:
      model: gemini/gemini-2.5-flash
      api_key: os.environ/GEMINI_API_KEY

  # Alias para compatibilidade
  - model_name: openai/gpt-4o-mini
    litellm_params:
      model: gemini/gemini-2.5-flash
      api_key: os.environ/GEMINI_API_KEY

  # Modelo de embedding para RAG
  - model_name: kb-embedding
    litellm_params:
      model: gemini/gemini-embedding-2
      api_key: os.environ/GEMINI_API_KEY

litellm_settings:
  drop_params: true  # Ignora parâmetros não suportados
```

### `.litellm/.env`

```bash
LITELLM_MASTER_KEY=sk-local-development
GEMINI_API_KEY=sua-chave-aqui
```

## Como Adicionar um Modelo

### 1. Adicionar chave de API no `.litellm/.env`

```bash
# Adicionar a chave do provedor
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
```

### 2. Adicionar modelo no `.litellm/config.yaml`

```yaml
model_list:
  # Modelo existente
  - model_name: chat-default
    litellm_params:
      model: gemini/gemini-2.5-flash
      api_key: os.environ/GEMINI_API_KEY

  # Novo modelo OpenAI
  - model_name: gpt-4o
    litellm_params:
      model: openai/gpt-4o
      api_key: os.environ/OPENAI_API_KEY

  # Novo modelo Anthropic
  - model_name: claude-sonnet
    litellm_params:
      model: anthropic/claude-sonnet-4-20250514
      api_key: os.environ/ANTHROPIC_API_KEY

  # Novo modelo local (Ollama)
  - model_name: llama-local
    litellm_params:
      model: ollama/llama3.1
      api_base: http://host.docker.internal:11434

  # Novo embedding
  - model_name: openai-embedding
    litellm_params:
      model: openai/text-embedding-3-small
      api_key: os.environ/OPENAI_API_KEY
```

### 3. Reiniciar o LiteLLM

```bash
docker compose restart litellm
```

### 4. Usar o modelo

```bash
# Via API direta
curl http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-local-development" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Olá!"}]
  }'

# No agents (variável de ambiente)
AGENTS_LITELLM_MODEL=gpt-4o

# No backend (variável de ambiente)
BACKEND_LITELLM_MODEL=gpt-4o
```

## Formato do `config.yaml`

### Estrutura Básica

```yaml
model_list:
  - model_name: nome-alias       # Nome que o sistema usa
    litellm_params:
      model: provedor/modelo     # Modelo real no provedor
      api_key: os.environ/VAR    # Chave via variável de ambiente
      # Parâmetros opcionais
      temperature: 0.7
      max_tokens: 4096
      api_base: http://...       # Para modelos locais

litellm_settings:
  drop_params: true   # Ignora params não suportados
  timeout: 30         # Timeout em segundos
```

### Provedores Suportados

| Provedor | Prefixo | Exemplo |
|---|---|---|
| Google Gemini | `gemini/` | `gemini/gemini-2.5-flash` |
| OpenAI | `openai/` | `openai/gpt-4o` |
| Anthropic | `anthropic/` | `anthropic/claude-sonnet-4-20250514` |
| Ollama | `ollama/` | `ollama/llama3.1` |
| OpenRouter | `openrouter/` | `openrouter/meta-llama/llama-3.1-405b-instruct` |
| Azure | `azure/` | `azure/gpt-4o` |
| Bedrock | `bedrock/` | `bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0` |

### Variáveis de Ambiente no Config

Use `os.environ/NOME_VARIAVEL` para referenciar variáveis:

```yaml
api_key: os.environ/GEMINI_API_KEY      # Lê de $GEMINI_API_KEY
api_key: os.environ/OPENAI_API_KEY      # Lê de $OPENAI_API_KEY
api_base: os.environ/OLLAMA_API_BASE    # Lê de $OLLAMA_API_BASE
```

## Como Usar nos Serviços

### Agents

O agents usa o modelo definido em `AGENTS_LITELLM_MODEL`:

```python
# agents/agents/customer_service.py
self._llm = ChatOpenAI(
    model=self._settings.litellm_model,  # ← AGENTS_LITELLM_MODEL
    base_url=f"{self._settings.litellm_url}/v1",
    api_key=self._settings.litellm_api_key,
)
```

Para trocar o modelo do agents:
```bash
# No .env
AGENTS_LITELLM_MODEL=gpt-4o
```

### Backend (Compressão de Memória)

O backend usa o modelo definido em `BACKEND_LITELLM_MODEL` para comprimir memória:

```bash
# No .env
BACKEND_LITELLM_MODEL=openai/gpt-4o-mini
```

### Embedding (RAG)

Tanto agents quanto backend usam `kb-embedding` para embeddings:

```python
# agents/agents/knowledge.py
OpenAIEmbeddings(
    model=self._settings.embedding_model,  # ← kb-embedding
    base_url=f"{self._settings.litellm_url}/v1",
)
```

Para trocar o modelo de embedding:
```bash
# No .env
AGENTS_EMBEDDING_MODEL=openai-embedding
BACKEND_EMBEDDING_MODEL=openai-embedding
```

E adicionar o modelo no config.yaml:
```yaml
- model_name: openai-embedding
  litellm_params:
    model: openai/text-embedding-3-small
    api_key: os.environ/OPENAI_API_KEY
```

## Testar o LiteLLM

### Health Check

```bash
curl http://localhost:4000/health
```

### Listar Modelos

```bash
curl http://localhost:4000/v1/models \
  -H "Authorization: Bearer sk-local-development"
```

### Testar Chat

```bash
curl http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-local-development" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "chat-default",
    "messages": [
      {"role": "system", "content": "Responda em português."},
      {"role": "user", "content": "Qual é a capital do Brasil?"}
    ]
  }'
```

### Testar Embedding

```bash
curl http://localhost:4000/v1/embeddings \
  -H "Authorization: Bearer sk-local-development" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "kb-embedding",
    "input": "taxa do empréstimo consignado"
  }'
```

## Exemplos Práticos

### Trocar de Gemini para OpenAI

1. Adicionar `OPENAI_API_KEY` no `.litellm/.env`:
```bash
OPENAI_API_KEY=sk-...
```

2. Atualizar `.litellm/config.yaml`:
```yaml
model_list:
  - model_name: chat-default
    litellm_params:
      model: openai/gpt-4o-mini    # ← mudou de gemini para openai
      api_key: os.environ/OPENAI_API_KEY

  - model_name: kb-embedding
    litellm_params:
      model: openai/text-embedding-3-small    # ← mudou embedding
      api_key: os.environ/OPENAI_API_KEY
```

3. Reiniciar:
```bash
docker compose restart litellm
```

### Adicionar Modelo Local (Ollama)

1. Instalar Ollama na máquina host: https://ollama.com

2. Puxar o modelo:
```bash
ollama pull llama3.1
```

3. Adicionar no `.litellm/config.yaml`:
```yaml
- model_name: llama-local
  litellm_params:
    model: ollama/llama3.1
    api_base: http://host.docker.internal:11434
```

4. Reiniciar:
```bash
docker compose restart litellm
```

5. Usar:
```bash
AGENTS_LITELLM_MODEL=llama-local
```

### Adicionar OpenRouter

1. Obter chave em https://openrouter.ai/keys

2. Adicionar no `.litellm/.env`:
```bash
OPENROUTER_API_KEY=sk-or-...
```

3. Adicionar no `.litellm/config.yaml`:
```yaml
- model_name: llama-openrouter
  litellm_params:
    model: openrouter/meta-llama/llama-3.1-405b-instruct
    api_key: os.environ/OPENROUTER_API_KEY
```

## Troubleshooting

### Modelo não encontrado

```bash
# Listar modelos disponíveis
curl http://localhost:4000/v1/models \
  -H "Authorization: Bearer sk-local-development"
```

Verificar se o `model_name` no config.yaml corresponde ao usado.

### Erro de autenticação

Verificar se a chave de API está correta no `.litellm/.env`:

```bash
cat .litellm/.env
```

### Timeout

Aumentar timeout no config.yaml:

```yaml
litellm_settings:
  timeout: 60  # segundos
```

Ou no .env:
```bash
AGENTS_MCP_TIMEOUT_SECONDS=60
```

### LiteLLM não inicia

```bash
# Verificar logs
docker compose logs litellm

# Verificar sintaxe do config.yaml
cat .litellm/config.yaml
```
