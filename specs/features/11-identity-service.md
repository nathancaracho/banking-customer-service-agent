# Feature 11 - Identity service

Como plataforma bancária, quero centralizar autenticação contextual, resolução
de roles e autorização de tools em um serviço único, para aplicar políticas de
acesso de forma consistente em todo o sistema.

Impacta: `frontend`, `backend`, `agents`, `identity`
Stack principal: `FastAPI`, `SQLAlchemy`, `PostgreSQL`, `AgentMiddleware`

## 1. Objetivo

Definir o serviço `Identity` como fonte de verdade para validação de contexto de
autenticação, resolução de papéis e decisões de autorização consumidas pelo
backend e pelo `CustomerServiceAgent`.

## 2. Escopo

Esta feature cobre:

- validação do contexto de autenticação recebido pelo backend;
- resolução de usuário, roles e permissões;
- contrato de autorização consumido pelo middleware do agente;
- persistência de usuários, roles, permissões e políticas;
- auditoria das validações e decisões do `Identity`.

## 3. Fora de escopo

Esta feature não cobre:

- tela administrativa completa de usuários e roles;
- provedor externo de identidade;
- emissão de tokens pelo frontend;
- implementação visual de login;
- lógica interna de ferramentas bancárias.

## 4. Atores envolvidos

- usuário autenticado;
- frontend;
- backend;
- `CustomerServiceAgent`;
- middleware do agente;
- serviço `Identity`;
- PostgreSQL.

## 5. Dependências

- Feature 06 - RBAC;
- Feature 07 - Auditoria;
- Feature 08 - Observabilidade;
- Feature 10 - Segurança e guardrails;
- persistência no schema `identity`.

## 6. Premissas

- o `Identity` é a fonte de verdade para roles, permissões e políticas;
- backend e agente não inferem autorização sem consultar o `Identity`;
- falhas de validação ou autorização resultam em bloqueio seguro;
- uma autorização vale somente para a ação, recurso e parâmetros avaliados;
- decisões do `Identity` são consumidas de forma síncrona no fluxo crítico.

## 7. Fluxo principal

1. O frontend envia uma requisição autenticada ao backend.
2. O backend envia o contexto de autenticação ao `Identity`.
3. O `Identity` valida o contexto e resolve o usuário e suas roles.
4. O backend prossegue com o chat usando o contexto validado.
5. Quando o agente decide chamar uma tool protegida, o middleware envia a
   intenção ao `Identity`.
6. O `Identity` avalia ação, recurso, parâmetros e permissões.
7. O `Identity` retorna a decisão.
8. Se a decisão for positiva, o agente chama a tool pelo MCP.
9. Se a decisão for negativa, a tool não é executada.

## 8. Fluxos alternativos

- sessão válida reutilizada em múltiplas mensagens do mesmo chat;
- role com acesso administrativo explícito a determinada ação;
- recurso ambíguo exige esclarecimento antes da decisão;
- ferramenta pública ou não protegida segue sem checagem específica.

## 9. Fluxos de erro

- token inválido ou expirado;
- contexto de autenticação malformado;
- usuário inexistente;
- `Identity` indisponível;
- permissão removida entre uma interação e outra;
- parâmetros alterados após a decisão inicial.

## 10. Regras de negócio

- o backend valida autenticação com o `Identity` antes de abrir o fluxo de chat;
- o agente consulta o `Identity` antes de qualquer tool protegida;
- uma decisão positiva não autoriza outras tools automaticamente;
- o `Identity` falha fechado;
- o token bruto não deve ser persistido em logs ou auditoria comum.

## 11. Requisitos funcionais

- RF-01: validar contexto de autenticação recebido pelo backend.
- RF-02: resolver `user_id`, roles e permissões ativas.
- RF-03: autorizar ou negar tool calls do agente.
- RF-04: retornar motivo técnico da decisão para consumo interno.
- RF-05: registrar validações e decisões para auditoria.
- RF-06: suportar políticas versionadas.

## 12. Requisitos não funcionais

- baixa latência para validação e autorização;
- decisões determinísticas para o mesmo contexto e mesma policy;
- alta disponibilidade compatível com o caminho crítico do sistema;
- escalabilidade independente de backend e agents;
- minimização de dados sensíveis em trânsito e logs.

## 13. Contratos / interfaces

Validação de contexto:

```json
{
  "auth_context": "opaque-token-or-session",
  "request_id": "uuid",
  "chat_id": "uuid"
}
```

Resposta:

```json
{
  "valid": true,
  "subject": {
    "user_id": "usr_123",
    "roles": ["customer"]
  },
  "policy_version": "2026-06-29"
}
```

Autorização de tool:

```json
{
  "subject": {
    "user_id": "usr_123",
    "roles": ["customer"]
  },
  "action": "card_limit.update",
  "resource": {
    "type": "credit_card",
    "owner_id": "usr_123"
  },
  "parameters": {
    "requested_limit": 15000
  },
  "context": {
    "request_id": "uuid",
    "chat_id": "uuid",
    "tool_name": "update_card_limit"
  }
}
```

## 14. Modelo de dados necessário

- `User`;
- `Role`;
- `Permission`;
- `UserRole`;
- `RolePermission`;
- `PolicyVersion`;
- `AuthorizationDecision`.

## 15. Eventos e auditoria

- `identity.context_validated`;
- `identity.context_rejected`;
- `identity.authorization_allowed`;
- `identity.authorization_denied`;
- `identity.authorization_error`;
- `identity.policy_version_used`.

## 16. Observabilidade

- latência de validação de contexto;
- latência de autorização por action;
- taxa de `allow` e `deny`;
- falhas fechadas;
- indisponibilidade do `Identity`;
- correlação por `trace_id`, `request_id` e `chat_id`.

## 17. Segurança e autorização

- não confiar em `user_id` enviado pelo frontend sem validação;
- não expor detalhes desnecessários da policy ao usuário final;
- proteger credenciais e segredos do `Identity`;
- aplicar least privilege na própria operação do serviço;
- garantir que o middleware do agente bloqueie a tool quando a decisão não for
  positiva.

## 18. Critérios de aceite

- backend consegue validar contexto com o `Identity` antes do chat;
- agente consulta `Identity` antes de tool protegida;
- tool protegida não executa quando a decisão for negativa;
- decisões e validações são auditáveis;
- indisponibilidade do `Identity` impede o acesso protegido.

## 19. Casos de teste sugeridos

- validar contexto autenticado válido;
- rejeitar token expirado;
- autorizar consulta do próprio recurso;
- negar acesso a recurso de terceiro;
- negar tool call quando o `Identity` estiver indisponível;
- verificar auditoria da validação e da autorização.

## 20. Open questions

- o backend envia o token bruto ao worker ou um contexto já reduzido e validado?
- o `Identity` será acessado diretamente pelo backend em todas as rotas
  administrativas ou haverá cache intermediário?
- existe necessidade de revogação imediata de sessão entre uma mensagem e outra
  no mesmo chat?
