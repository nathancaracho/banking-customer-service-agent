# Stack técnica

## Objetivo

Documentar a stack técnica adotada ou planejada para cada projeto do monorepo,
explicando onde cada biblioteca entra e por que ela foi escolhida.

## Princípios de escolha

- manter o número de dependências baixo;
- preferir bibliotecas consolidadas e simples de operar;
- preservar os limites entre `frontend`, `backend`, `agents` e `identity`;
- centralizar responsabilidades transversais em pontos explícitos;
- evitar acoplamento do chat ao estado interno do agente.

## Estado atual do repositório

Os itens abaixo refletem o que já aparece nos manifests e na infraestrutura
versionada do repositório no momento desta escrita.

## Projetos do monorepo

### Frontend

**Projeto:** `frontend`

**Bibliotecas atuais:**

- `react` e `react-dom`
- `vite`
- `typescript`
- `assistant-ui`
- `shadcn`
- `eslint` e plugins de lint

**Uso no projeto:**

- `React` e `React DOM` sustentam a aplicação de chat e as telas
  administrativas.
- `Vite` acelera desenvolvimento local e build do frontend.
- `TypeScript` dá contratos mais seguros para eventos, payloads e telas.
- `assistant-ui` acelera a montagem da experiência de chat.
- `shadcn` serve como base para componentes de interface e telas de gestão.

**Por que esta stack:**

- rápida para iterar em demo e entrevista;
- boa ergonomia para chat e telas auxiliares;
- tipagem ajuda nos contratos de SSE e estados da UI;
- baixa complexidade operacional.

**Observações:**

- a comunicação com o backend deve usar HTTPS e SSE;
- o frontend não acessa filas, banco ou tools diretamente.

### Backend

**Projeto:** `backend`

**Bibliotecas atuais:**

- `fastapi`
- `sqlalchemy`
- `alembic`
- `asyncpg`
- `langchain-text-splitters`
- `langchain-chroma`
- `langchain-openai`
- `pytest`

**Uso no projeto:**

- `FastAPI` expõe APIs HTTP e o stream SSE.
- `SQLAlchemy` modela chats, mensagens, resumos e metadados.
- `Alembic` versiona o schema do backend.
- `asyncpg` é o driver PostgreSQL assíncrono.
- `langchain-text-splitters` aplica o chunking da base de conhecimento.
- `langchain-chroma` integra a base vetorial ao Chroma por meio do client
  oficial.
- `langchain-openai` gera embeddings pelo endpoint OpenAI-compatible do
  `LiteLLM`.
- `pytest` cobre testes do projeto Python.

**Por que esta stack:**

- `FastAPI` simplifica APIs assíncronas e contratos HTTP;
- `SQLAlchemy` + `Alembic` é um conjunto maduro para persistência relacional;
- `asyncpg` é adequado para I/O assíncrono com PostgreSQL;
- combina bem com o papel do backend como fronteira pública do sistema.

**Dependências técnicas planejadas:**

- cliente RabbitMQ para publicar na `request_queue` e consumir a
  `reply_queue`;
- uso explícito de SSE com os recursos do ecossistema FastAPI/Starlette;
- integração com `LiteLLM` para compressão da memória do chat.

### Agents

**Projeto:** `agents`

**Bibliotecas atuais:**

- `aio-pika`
- `fastmcp`
- `httpx`
- `langchain`
- `langchain-openai`
- `pydantic-settings`

**Uso no projeto:**

- `aio-pika` conecta o worker às filas `request_queue` e `reply_queue`.
- `FastMCP` fornece o cliente das tools expostas pelo `mcp_proxy`.
- `HTTPX` integra o Agent ao `Identity` e ao Chroma HTTP API.
- `LangChain` sustenta o `CustomerServiceAgent`.
- `langchain-openai` permite falar com um endpoint compatível com OpenAI,
  incluindo o gateway do `LiteLLM`.
- `pydantic-settings` centraliza a carga de configuração do worker.

**Por que esta stack:**

- acelera a construção do agent sem obrigar um framework pesado de multi-agent;
- suporta model providers distintos via interface compatível;
- permite middleware para preocupações transversais, como autorização e HIL.
- mantém a integração com filas, Identity e MCP explícita e pequena.

**Dependências técnicas planejadas:**

- middleware explícito do agent para autorização antes de tool call;
- integração com `LiteLLM` como gateway de embeddings e modelos;
- checkpointer compatível com fluxo de confirmação humana.

### Identity

**Projeto:** `identity`

**Bibliotecas atuais:**

- ainda sem dependências declaradas no manifest

**Stack planejada:**

- `FastAPI`
- `SQLAlchemy`
- `Alembic`
- biblioteca de validação de contexto de autenticação compatível com o provedor
  escolhido

**Uso no projeto:**

- validar contexto de autenticação;
- resolver usuário, roles e permissões;
- decidir autorizações consumidas pelo backend e pelo agent;
- persistir usuários, roles, permissões e políticas.

**Por que esta stack:**

- mantém consistência com os demais serviços Python;
- reduz custo cognitivo no monorepo;
- facilita compartilhar convenções de API, migrations e testes.

### Banking API

**Projeto:** `banking_api`

**Bibliotecas atuais:**

- `FastAPI`
- `SQLAlchemy`
- `Alembic`
- `psycopg2`

**Uso no projeto:**

- simular perfil, saldo, limite de cartão e transferências PIX;
- manter estado mutável para demonstrações e testes locais;
- servir como sistema bancário interno consumido pelo MCP Proxy.

**Por que esta stack:**

- mantém a API fake pequena e explícita;
- permite demonstrar mutações reais no PostgreSQL;
- evita adicionar regras de negócio falsas dentro do Agent ou do MCP Proxy.

### MCP Proxy

**Projeto:** `mcp_proxy`

**Bibliotecas atuais:**

- `FastMCP`
- `HTTPX`
- `Pydantic`

**Uso no projeto:**

- expor as tools bancárias pelo protocolo MCP;
- validar contratos de entrada das tools;
- traduzir tool calls em chamadas HTTP para a `banking_api`;
- normalizar falhas da Banking API.

**Por que esta stack:**

- atende explicitamente ao requisito de MCP do desafio;
- mantém o Agent desacoplado dos contratos HTTP bancários;
- permite escalar ou substituir o proxy sem alterar o Agent.

## Infraestrutura compartilhada

### PostgreSQL

**Definição atual:** `docker-compose.yml`

**Uso:**

- `backend`: chats, mensagens e resumos;
- `agents`: checkpoints;
- `identity`: usuários, roles, permissões, políticas e auditoria.

**Por que usar:**

- forte aderência a dados relacionais e auditáveis;
- uma instância com schemas separados simplifica a operação para o desafio;
- ótimo suporte com SQLAlchemy e Alembic.

### RabbitMQ

**Definição atual:** `docker-compose.yml`

**Uso:**

- `request_queue` para solicitações do backend aos workers;
- `reply_queue` para chunks e eventos do agent de volta ao backend.

**Por que usar:**

- desacopla conexões HTTP do tempo de execução do agent;
- facilita escala independente de backend e workers;
- combina com o padrão de request/reply assíncrono do projeto.

### Chroma

**Definição atual:** `docker-compose.yml`

**Uso:**

- armazenamento de documentos e embeddings da KB;
- retrieval usado pelo `CustomerServiceAgent`.

**Por que usar:**

- simples de subir localmente para demo;
- suficiente para o caso de uso de KB do desafio;
- reduz esforço operacional para uma prova técnica.

### LiteLLM

**Definição atual:** `docker-compose.yml`

**Uso:**

- gateway de modelos para o agent;
- compressão de memória feita pelo backend;
- fallback ou troca de provider sem alterar contratos de alto nível.

**Por que usar:**

- reduz acoplamento a um provider específico;
- facilita demo com provider pago, local ou mock;
- permite manter uma interface unificada para modelos.

### SigNoz / OpenTelemetry

**Definição atual:** `observability/`, `docker-compose.yml`, `observability/docker-compose.signoz.yaml`

**Uso:**

- coleta de traces, métricas e logs via OTLP gRPC;
- UI em `http://localhost:3301` para inspeção ponta a ponta;
- pacote compartilhado `observability` instrumentando `backend`, `agents`, `identity` e `mcp_proxy`;
- propagação de contexto W3C em mensagens RabbitMQ.

**Por que usar:**

- atende o requisito de observabilidade do desafio com stack compatível com OpenTelemetry;
- permite correlacionar HTTP, SSE, filas, autorização e tools MCP;
- mantém a instrumentação centralizada e reutilizável entre serviços Python.

## Mapeamento rápido por responsabilidade

| Responsabilidade | Projeto principal | Stack principal |
| --- | --- | --- |
| Chat, SSE e memória | `backend` | `FastAPI`, `SQLAlchemy`, `PostgreSQL`, `RabbitMQ`, `LiteLLM` |
| Execução do agent | `agents` | `LangChain`, `langchain-openai`, `LiteLLM`, `RabbitMQ` |
| Autorização e roles | `identity` | `FastAPI`, `SQLAlchemy`, `PostgreSQL` |
| Core bancário fake | `banking_api` | `FastAPI`, `SQLAlchemy`, `PostgreSQL` |
| Tools bancárias | `mcp_proxy` | `FastMCP`, `HTTPX`, `Pydantic` |
| UI do chat e admin | `frontend` | `React`, `Vite`, `TypeScript`, `assistant-ui`, `shadcn` |
| KB/RAG | `agents` + infra | `LangChain`, `Chroma`, `LiteLLM` |

## Decisões relacionadas

- [ADR 001 - Agent middleware](adrs/001-agent-middleware.md)
- [ADR 002 - Chat memory in backend](adrs/002-chat-memory-in-backend.md)
- [ADR 003 - Identity before tool call](adrs/003-identity-before-tool-call.md)
