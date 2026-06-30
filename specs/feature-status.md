# Status das features

Atualizado em: 30/06/2026

Este arquivo acompanha o estado da implementação. As specs em
[`features/`](features/README.md) continuam sendo a fonte de verdade do
comportamento esperado.

## Estado atual

- [x] Infraestrutura local com PostgreSQL, RabbitMQ, Chroma e LiteLLM.
- [x] Serviço `identity` executando no Docker Compose.
- [x] Serviço `backend` executando no Docker Compose.
- [x] Migrations separadas nos schemas `identity` e `backend`.
- [x] Fluxo Backend → RabbitMQ → resposta mockada → SSE validado.
- [ ] Worker com `CustomerServiceAgent` consumindo a fila.
- [x] MCP Proxy com FastMCP.
- [x] Banking API fake e stateful.
- [x] Frontend funcional para login, chats e streaming SSE.
- [ ] Observabilidade com traces, métricas e logs correlacionados.

## Feature 01 — Conversação e experiência do chat

Status: em andamento.

- [x] Autenticação JWT na borda do Backend.
- [x] Criar chat.
- [x] Listar somente os chats do usuário autenticado.
- [x] Abrir chat com validação de ownership.
- [x] Persistir mensagens do usuário.
- [x] Montar payload com resumo e mensagens recentes.
- [x] Publicar solicitações na `agent.requests`.
- [x] Consumir eventos da `agent.replies`.
- [x] Transmitir chunks por SSE.
- [x] Ordenar chunks pelo campo `sequence`.
- [x] Descartar chunks duplicados já processados.
- [x] Persistir resposta do agente somente após `completed`.
- [x] Tratar timeout do agente com evento `failed`.
- [x] Implementar login de demonstração no Frontend.
- [x] Criar, listar e abrir chats no Frontend.
- [x] Integrar o chat com `assistant-ui` e componentes `shadcn`.
- [x] Consumir o streaming SSE no Frontend.
- [ ] Conectar um worker real ao fluxo.
- [ ] Atualizar o status da mensagem quando a publicação falhar.
- [ ] Preservar formalmente respostas parciais após falha.
- [ ] Implementar compressão de memória via LiteLLM.
- [ ] Implementar cancelamento.
- [ ] Implementar reconexão e retomada do SSE.
- [ ] Implementar nova tentativa explícita.

## Feature 02 — Resposta RAG

Status: não iniciada.

- [ ] Implementar ingestão e retrieval no Agent.
- [ ] Responder com conteúdo fundamentado.
- [ ] Retornar citações das fontes utilizadas.
- [ ] Tratar ausência de contexto suficiente.
- [ ] Testar grounding e alucinação.

## Feature 03 — Aumento de limite

Status: não iniciada.

- [ ] Consultar perfil e limite atual pelo MCP Proxy.
- [ ] Verificar elegibilidade.
- [ ] Solicitar confirmação explícita.
- [ ] Persistir checkpoint para HIL.
- [ ] Executar aumento autorizado.
- [ ] Retomar a execução após confirmação.

## Feature 04 — Controle de acesso

Status: parcialmente implementada no Identity.

- [x] Decisão `allow` para recurso próprio.
- [x] Decisão `deny` para recurso de terceiro.
- [x] Negativa para contexto inválido.
- [x] Registro da decisão de autorização.
- [ ] Integrar o middleware do Agent ao Identity.
- [ ] Garantir que uma negativa impeça a chamada ao MCP Proxy.
- [ ] Cobrir indisponibilidade do Identity com falha fechada.

## Feature 05 — PIX crítico

Status: não iniciada.

- [ ] Criar contrato da operação PIX no MCP Proxy.
- [ ] Validar limites e risco.
- [ ] Exigir autenticação adicional quando aplicável.
- [ ] Solicitar confirmação explícita.
- [ ] Persistir e retomar checkpoint.
- [ ] Impedir retry automático após resultado ambíguo.

## Feature 06 — RBAC

Status: parcialmente implementada.

- [x] Models de usuários, roles e permissões.
- [x] Roles `customer`, `manager` e `admin`.
- [x] Matriz inicial de permissões via migration.
- [x] Avaliação por ação, recurso e ownership.
- [x] Política versionada.
- [ ] Completar cenários de `manager`.
- [ ] Completar cenários de `admin`.
- [ ] Definir o fluxo administrativo de atribuição de roles.
- [ ] Integrar telas administrativas do Frontend.

## Feature 07 — Auditoria

Status: parcialmente implementada no Identity.

- [x] Persistir decisões de autorização.
- [x] Registrar `request_id`, `chat_id`, usuário, ação e policy.
- [ ] Registrar eventos do Backend.
- [ ] Registrar execução de tools no MCP Proxy.
- [ ] Mascarar dados sensíveis de forma consistente.
- [ ] Expor consulta administrativa da trilha de auditoria.

## Feature 08 — Observabilidade

Status: não iniciada.

- [ ] Adicionar OpenTelemetry.
- [ ] Propagar `trace_id`, `request_id` e `chat_id`.
- [ ] Instrumentar Backend, Agent, Identity e MCP Proxy.
- [ ] Medir conexões SSE e tempo até o primeiro chunk.
- [ ] Medir profundidade e espera das filas.
- [ ] Medir latência e erros por tool.
- [ ] Subir e configurar SigNoz.

## Feature 09 — Contratos MCP

Status: proxy implementado, integração com o Agent pendente.

- [x] Catálogo inicial de tools documentado.
- [x] MCP Proxy incluído no diagrama.
- [x] Criar o projeto do MCP Proxy.
- [x] Criar a Banking API fake.
- [x] Persistir perfil, saldo, limite e PIX no PostgreSQL.
- [x] Implementar `get_customer_profile`.
- [x] Implementar `get_balance`.
- [x] Implementar `get_card_limit`.
- [x] Implementar `update_card_limit`.
- [x] Implementar `create_pix`.
- [x] Normalizar respostas e erros HTTP.
- [x] Integrar a Banking API fake.
- [ ] Integrar o cliente MCP ao Agent.
- [ ] Testar timeout ambíguo em operações mutáveis.

## Feature 10 — Segurança e guardrails

Status: parcialmente implementada.

- [x] Backend não aceita `user_id` do payload como identidade.
- [x] Ownership de chat validado no servidor.
- [x] Token ausente ou inválido retorna `401`.
- [x] SQLite rejeitado no código de produção.
- [x] Configurações obrigatórias falham cedo.
- [ ] Implementar limites e rate limiting.
- [ ] Implementar sanitização de entrada e saída do Agent.
- [ ] Garantir mascaramento em logs e traces.
- [ ] Implementar proteção contra prompt injection.
- [ ] Testar bypass de autorização e vazamento de dados.

## Feature 11 — Identity

Status: funcional, integração pendente.

- [x] Serviço FastAPI.
- [x] PostgreSQL no schema `identity`.
- [x] Alembic executado antes da aplicação.
- [x] Models e migration inicial.
- [x] Validação de contexto.
- [x] Decisão de autorização.
- [x] Auditoria de decisões.
- [x] Testes de autorização positiva e negativa.
- [ ] Revisar a divisão entre autenticação do Backend e validação do Identity.
- [ ] Integrar o middleware do Agent.
- [ ] Adicionar healthcheck e observabilidade.
- [ ] Testar falha fechada em integração real.

## Feature 12 — Ingestão e gestão da KB

Status: não iniciada.

- [ ] Implementar upload de arquivos.
- [ ] Validar tipo e tamanho.
- [ ] Extrair e normalizar conteúdo.
- [ ] Aplicar chunk size `700` e overlap `200`.
- [ ] Gerar embeddings com Gemini via LiteLLM.
- [ ] Indexar no Chroma.
- [ ] Gerenciar ativação e remoção de documentos.
- [ ] Criar tela administrativa da base de conhecimento.

## Próximos passos

- [ ] Implementar o worker do `CustomerServiceAgent`.
- [ ] Consumir `agent.requests` e publicar chunks em `agent.replies`.
- [ ] Integrar o middleware de autorização ao Identity.
- [x] Criar o MCP Proxy e as APIs bancárias fake.
- [ ] Substituir a resposta mockada pelo Agent real.
- [x] Conectar o Frontend ao Backend.
