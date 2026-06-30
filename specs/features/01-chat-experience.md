# Feature 01 — Conversação e experiência do chat

Como usuário autenticado, quero continuar uma conversa com o agente sem repetir
todo o contexto, recebendo respostas progressivas e estados claros durante o
atendimento.

Domínio principal: `chat`
Projeto principal: `backend`
Impacta: `frontend`, `backend`, `agents`
Stack principal: `React`, `assistant-ui`, `FastAPI`, `RabbitMQ`, `PostgreSQL`, `SSE`

## 1. Objetivo

Permitir conversas contínuas, autenticadas e progressivas, preservando o
contexto do chat e apresentando estados claros ao usuário.

## 2. Escopo

- criação e retomada de chats;
- envio e persistência de mensagens;
- memória com resumo e janela recente;
- referências elípticas, como “e o meu limite?”;
- streaming por SSE;
- timeout, cancelamento e mensagens de erro.

## 3. Fora de escopo

- prompt e reasoning loop do agente;
- algoritmo de compressão;
- pipeline interno de RAG;
- interface visual detalhada.

## 4. Atores envolvidos

- usuário autenticado;
- frontend;
- backend;
- `CustomerServiceAgent`;
- LiteLLM;
- PostgreSQL.

## 5. Dependências

- autenticação válida;
- `request_queue` e `reply_queue`;
- persistência no schema `backend`;
- specs de auditoria, observabilidade e segurança.

## 6. Premissas

- um `chat_id` pertence a um único usuário;
- o backend é a fonte de verdade do histórico;
- uma nova execução recebe um novo `request_id`;
- o frontend pode reconectar o stream sem alterar o conteúdo persistido.

## 7. Fluxo principal

1. O frontend abre ou cria um chat.
2. O usuário envia uma mensagem.
3. O backend valida o acesso ao `chat_id` e persiste a mensagem.
4. O backend monta a memória e publica a solicitação.
5. O agente publica chunks numerados.
6. O backend encaminha os eventos por SSE.
7. O backend persiste a resposta ao receber `completed`.

## 8. Fluxos alternativos

- Chat novo: `summary` e mensagens recentes ficam vazios.
- Chat longo: o backend atualiza o resumo antes de publicar a solicitação.
- Referência elíptica: o agente recebe contexto suficiente para resolvê-la.
- Cancelamento: o frontend solicita cancelamento e a interface encerra o stream.
- Reconexão SSE: o frontend recupera o estado persistido e continua a exibição.

## 9. Fluxos de erro

- `chat_id` inexistente ou de outro usuário: negar sem revelar sua existência.
- Falha antes da publicação: marcar a mensagem como falha.
- Timeout do agente: emitir `failed` com mensagem recuperável.
- Falha após chunks parciais: preservar o conteúdo apenas como resposta
  incompleta, sem tratá-lo como resposta final.
- Evento fora de ordem: ordenar a apresentação pelo `sequence`.

## 10. Regras de negócio

- Apenas o proprietário ou um perfil autorizado acessa o chat.
- A mensagem do usuário é persistida antes da publicação.
- Somente o evento `completed` produz uma resposta final.
- O resumo nunca substitui o histórico persistido.
- O conteúdo de outro chat não pode compor a memória atual.

## 11. Requisitos funcionais

- RF-01: criar, listar, abrir e continuar chats autorizados.
- RF-02: manter contexto entre mensagens do mesmo chat.
- RF-03: transmitir respostas progressivamente.
- RF-04: exibir estados de processamento, confirmação, conclusão e falha.
- RF-05: permitir nova tentativa explícita após erro recuperável.

## 12. Requisitos não funcionais

- O primeiro evento deve ser emitido dentro do timeout configurado.
- O stream não pode bloquear outros chats.
- O histórico deve sobreviver ao reinício do backend.
- A compressão deve respeitar o orçamento de contexto do modelo.

## 13. Contratos / interfaces

Entrada lógica:

```json
{
  "chat_id": "uuid",
  "content": "E qual é o meu limite?"
}
```

Evento SSE:

```json
{
  "request_id": "uuid",
  "chat_id": "uuid",
  "type": "chunk",
  "sequence": 1,
  "payload": {"content": "Seu limite atual"}
}
```

## 14. Modelo de dados necessário

- `Chat`: `id`, `user_id`, `created_at`, `updated_at`.
- `Message`: `id`, `chat_id`, `role`, `content`, `status`, `created_at`.
- `ChatSummary`: `chat_id`, `content`, `covered_until`, `updated_at`.

## 15. Eventos e auditoria

- `chat.created`;
- `message.submitted`;
- `request.completed`;
- `request.failed`;
- `chat.access_denied`.

Conteúdo integral de mensagens não deve ser incluído no evento de auditoria.

## 16. Observabilidade

- conexões SSE ativas;
- tempo até o primeiro chunk;
- duração da solicitação;
- quantidade de chunks;
- taxa de timeout e falha;
- execuções de compressão.

## 17. Segurança e autorização

- Validar autenticação e propriedade do chat em toda operação.
- Não aceitar `user_id` informado pelo frontend como fonte de identidade.
- Não registrar tokens, mensagens completas ou resumos em logs comuns.
- Aplicar limites de tamanho às mensagens.

## 18. Critérios de aceite

- Uma pergunta subsequente utiliza o contexto do mesmo chat.
- Chats diferentes permanecem isolados.
- Chunks são renderizados na ordem numérica.
- Uma falha parcial não é persistida como resposta final.
- O usuário recebe mensagem segura em timeout ou acesso negado.

## 19. Casos de teste sugeridos

- criar chat e concluir primeira mensagem;
- resolver referência elíptica;
- tentar acessar chat de outro usuário;
- receber chunks fora de ordem;
- falhar após resposta parcial;
- comprimir chat longo e preservar fatos relevantes.

## 20. Open questions

- Qual é o timeout inicial e total do stream?
- Qual orçamento de tokens dispara compressão?
- Cancelamento interrompe o processamento do worker ou apenas o stream?
