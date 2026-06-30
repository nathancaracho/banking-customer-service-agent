# Feature 08 - Observabilidade

Como time responsável pela plataforma, quero observar o fluxo ponta a ponta do
chat e das operações, para diagnosticar falhas e demonstrar escalabilidade.

Impacta: `backend`, `agents`, `identity`
Stack principal: `FastAPI`, `RabbitMQ`, `LiteLLM`, `OpenTelemetry-compatible observability stack`

## 1. Objetivo

Definir a instrumentação mínima para acompanhar saúde, latência, erros e custo do
produto de ponta a ponta, incluindo backend, filas, agente, `identity` e tools.

## 2. Escopo

Esta feature cobre:

- logs estruturados;
- métricas;
- traces distribuídos;
- correlação entre HTTP, SSE e filas;
- sinais mínimos para operação e diagnóstico.

## 3. Fora de escopo

Esta feature não cobre:

- operação completa de SRE;
- tuning detalhado de dashboards;
- retenção definitiva de observabilidade;
- profiling de baixo nível;
- detalhamento interno do reasoning do agente.

## 4. Atores envolvidos

- time de engenharia;
- avaliadores do desafio;
- backend;
- `Customer Service Agent`;
- `identity`;
- infraestrutura de observabilidade.

## 5. Dependências

- geração de `trace_id`;
- correlação por `chat_id` e `request_id`;
- instrumentação nos componentes principais;
- stack de observabilidade disponível no ambiente.

## 6. Premissas

- logs, métricas e traces têm papéis complementares;
- conteúdo sensível não deve ser exposto por padrão;
- filas fazem parte do caminho crítico e precisam ser observadas;
- SSE precisa de métricas próprias;
- custo de LLM e tools deve ser visível.

## 7. Fluxo principal

1. O frontend inicia uma requisição HTTP.
2. O backend cria ou propaga contexto de trace.
3. A mensagem é publicada na fila de request com identificadores de correlação.
4. O agent consome a mensagem e continua o trace lógico.
5. O agent consulta `identity`, `vector_db`, `LiteLLM` e MCP emitindo sinais
   operacionais.
6. O agent publica chunks na reply queue com o mesmo contexto de correlação.
7. O backend transmite SSE ao cliente e fecha a sessão com métricas consolidadas.

## 8. Fluxos alternativos

- requisição curta sem uso de tools ainda gera trace completo;
- consulta RAG sem operação crítica emite somente spans de leitura e resposta;
- fluxo com HIL gera spans separados para pausa e retomada.

## 9. Fluxos de erro

- timeouts em MCP ou `identity`;
- perda de chunk na reply queue;
- backend sem conexão SSE ativa para uma resposta tardia;
- erro do provedor LLM;
- falha de persistência de checkpoint.

## 10. Regras de negócio

- cada requisição deve ser rastreável de ponta a ponta;
- cada chunk publicado deve ser associado a `chat_id`, `request_id` e `sequence`;
- custo e uso de tokens devem ser observáveis quando o provider fornecer esse dado;
- operações críticas devem ter sinais específicos;
- conteúdo de mensagens deve ser minimizado nos logs.

## 11. Requisitos funcionais

- o sistema deve emitir logs estruturados;
- o sistema deve expor métricas de backend, agent, filas e tools;
- o sistema deve propagar contexto de correlação;
- deve existir visibilidade sobre tempo até primeiro chunk e tempo total de resposta;
- deve existir visibilidade sobre uso de tools e falhas por tipo.

## 12. Requisitos não funcionais

- instrumentação não deve degradar significativamente a latência;
- sinais devem ser consistentes entre instâncias;
- traces devem suportar fluxos assíncronos;
- dashboards devem ser suficientes para demo e troubleshooting;
- dados sensíveis devem ser mascarados.

## 13. Contratos / interfaces

Campos mínimos de correlação em logs e eventos operacionais:

```json
{
  "trace_id": "trc_123",
  "chat_id": "chat_123",
  "request_id": "chat_123",
  "component": "agents.customer_service",
  "event": "reply_chunk_published",
  "sequence": 3
}
```

Métricas mínimas esperadas:

- `chat_request_total`;
- `chat_time_to_first_chunk_ms`;
- `chat_response_duration_ms`;
- `queue_request_depth`;
- `queue_reply_depth`;
- `tool_call_total`;
- `tool_call_duration_ms`;
- `authorization_duration_ms`;
- `llm_token_usage_total`;
- `llm_cost_total`.

## 14. Modelo de dados necessário

- não exige novo banco dedicado;
- eventual armazenamento segue a stack de observabilidade escolhida;
- chaves de correlação devem existir nos componentes de negócio.

## 15. Eventos e auditoria

- início e fim de requisição de chat;
- publicação e consumo em filas;
- início e fim de tool call;
- decisão de autorização;
- início, pausa e retomada de operação crítica;
- falha de integração externa.

## 16. Observabilidade

- dashboard de latência do chat;
- dashboard de throughput e atraso de filas;
- dashboard de tools, `identity` e LLM;
- alerta para crescimento anormal de erros;
- alerta para ausência de consumidores ou aumento de backlog.

## 17. Segurança e autorização

- logs não devem conter tokens de autenticação;
- respostas de tools devem ser sanitizadas antes de logging;
- somente equipes autorizadas devem acessar painéis completos;
- traces não devem expor payload bancário completo;
- credenciais de observabilidade devem ficar fora do código.

## 18. Critérios de aceite

- uma requisição de chat pode ser rastreada do backend ao agent e de volta;
- é possível medir tempo até primeiro chunk;
- é possível medir falhas de autorização, MCP e LLM separadamente;
- filas possuem visibilidade de depth e consumo;
- a demo consegue mostrar ao menos um trace e métricas básicas do fluxo.

## 19. Casos de teste sugeridos

- validar propagação de `trace_id` em requisição simples;
- validar métrica de tempo até primeiro chunk;
- validar incremento de erro em falha de tool;
- validar correlação entre chunk publicado e chunk enviado por SSE;
- validar sanitização de logs;
- validar métricas para fluxo com HIL.

## 20. Open questions

- o teste precisa mostrar dashboard real em execução ou somente descrever a stack?
- qual nível de granularidade de custo por provider vale a pena demonstrar?
- a observabilidade do frontend vai entrar na demo ou o foco fica no backend e nos
  workers?
