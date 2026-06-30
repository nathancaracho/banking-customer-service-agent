# Feature 06 - RBAC

Como responsável pelo produto, quero que cada perfil tenha permissões claras e
previsíveis, para garantir acesso mínimo necessário e governança do sistema.

Domínio principal: `rbac`
Projeto principal: `identity`
Impacta: `frontend`, `backend`, `identity`
Stack principal: `FastAPI`, `SQLAlchemy`, `PostgreSQL`

## 1. Objetivo

Definir o modelo de controle de acesso baseado em papéis para o produto, garantindo
que cada usuário só consiga acessar dados e executar operações compatíveis com sua
role e com o escopo autorizado.

## 2. Escopo

Esta feature cobre:

- definição das roles `customer`, `manager` e `admin`;
- definição de permissões por capacidade de negócio;
- decisão de autorização feita pelo serviço `identity`;
- uso da decisão de autorização pelo `backend` e pelo `Customer Service Agent`;
- tela administrativa de consulta de usuários com visão resumida de saldo e
  limite;
- negação por padrão quando não houver permissão explícita.

## 3. Fora de escopo

Esta feature não cobre:

- UI completa de administração de usuários;
- engine de policy genérica configurável por linguagem externa;
- segregação por múltiplos tenants;
- regras internas de prompting do agente;
- desenho detalhado de onboarding de usuários.

## 4. Atores envolvidos

- usuário final com role `customer`;
- usuário interno com role `manager`;
- usuário interno com role `admin`;
- frontend;
- backend;
- `identity`;
- `Customer Service Agent`;
- sistemas internos expostos via MCP.

## 5. Dependências

- autenticação válida no frontend e no backend;
- serviço `identity` com base de usuários, roles e permissões;
- integração do agente com `identity` antes de qualquer tool sensível;
- persistência em PostgreSQL no schema de `identity`.

## 6. Premissas

- a role vem de uma fonte confiável validada por `identity`;
- permissões são avaliadas no servidor, nunca apenas no frontend;
- roles não substituem validações contextuais de negócio;
- acesso a dados de terceiros precisa de permissão explícita;
- operações críticas podem exigir confirmação adicional mesmo quando autorizadas.

## 7. Fluxo principal

1. O usuário autentica no frontend.
2. O backend recebe a sessão autenticada e encaminha a requisição de chat.
3. Quando o agente precisar acessar dado protegido ou executar uma operação, ele
   consulta `identity`.
4. `identity` avalia a role, o recurso solicitado e o escopo da ação.
5. `identity` devolve uma decisão de autorização.
6. O agente só continua a chamada de tool quando a decisão for `allow`.
7. O resultado final é devolvido ao backend e transmitido ao frontend.

## 8. Fluxos alternativos

- `manager` acessa dado de terceiro dentro do escopo permitido pela política.
- `admin` acessa função administrativa permitida pela policy.
- `customer` acessa apenas os próprios dados e operações associadas à própria conta.
- o backend pode consultar `identity` para rotas administrativas fora do chat.
- gerente e admin conseguem consultar a configuração financeira resumida do
  usuário na área administrativa;
- apenas `admin` pode alterar roles; `manager` visualiza, mas não edita.

## 9. Fluxos de erro

- token inválido ou expirado gera negativa imediata;
- usuário sem role atribuída recebe `deny`;
- recurso não reconhecido recebe `deny`;
- falha temporária de `identity` impede a execução de tools protegidas;
- conflito entre role e escopo do recurso gera negativa auditável.

## 10. Regras de negócio

- autorização é `deny by default`;
- permissões devem ser explícitas e avaliadas por ação e por recurso;
- `customer` não pode acessar dados de outro cliente;
- `manager` não recebe acesso universal por padrão;
- `admin` continua sujeito a trilha de auditoria e regras de negócio;
- autorização de role não substitui limite operacional, confirmação ou HIL.

## 11. Requisitos funcionais

- `identity` deve expor uma interface de decisão de autorização;
- o agente deve consultar `identity` antes de executar qualquer tool protegida;
- o backend deve usar a mesma base de roles em telas administrativas;
- a resposta de autorização deve informar decisão, motivo e contexto mínimo;
- o sistema deve suportar ao menos as roles `customer`, `manager` e `admin`.

## 12. Requisitos não funcionais

- a decisão de autorização deve ter baixa latência;
- a política precisa ser determinística para entradas iguais;
- toda negativa deve ser auditável;
- o comportamento deve ser consistente entre backend, agent e ferramentas;
- mudanças de policy precisam ser versionáveis.

## 13. Contratos / interfaces

Contrato lógico de autorização:

```json
{
  "subject": {
    "user_id": "usr_123",
    "role": "customer"
  },
  "action": "card_limit.update",
  "resource": {
    "type": "customer_account",
    "owner_id": "usr_123"
  },
  "context": {
    "chat_id": "chat_123",
    "request_id": "chat_123"
  }
}
```

Resposta:

```json
{
  "decision": "allow",
  "reason": "role_allows_own_resource",
  "policy_version": "2026-06-29",
  "subject": {
    "user_id": "usr_123",
    "role": "customer"
  }
}
```

## 14. Modelo de dados necessário

- `users`;
- `roles`;
- `user_roles`;
- `permissions`;
- `role_permissions`;
- `authorization_audit`.

## 15. Eventos e auditoria

- decisão de autorização emitida para leitura de dado protegido;
- decisão de autorização emitida para operação bancária;
- negativa por falta de role ou escopo;
- versão da policy usada na decisão;
- vínculo com `chat_id`, `request_id` e `user_id`.

## 16. Observabilidade

- taxa de decisões `allow` e `deny`;
- latência por decisão;
- negativas por action e por role;
- erros de integração entre agente e `identity`;
- correlação por `chat_id`, `request_id` e `trace_id`.

## 17. Segurança e autorização

- o frontend não é fonte de verdade para permissões;
- dados de roles não devem ser confiados sem validação do `identity`;
- o resultado da autorização deve ser aplicado antes da chamada ao MCP;
- respostas de erro não devem expor policy interna em excesso;
- mudanças de role devem ter rastreabilidade.

## 18. Critérios de aceite

- `customer` consegue acessar apenas recursos próprios;
- `customer` não consegue consultar saldo de terceiros;
- `manager` só acessa recursos previstos em policy;
- `admin` consegue executar funções administrativas permitidas;
- tools protegidas não são executadas quando a decisão for `deny`.

## 19. Casos de teste sugeridos

- autorizar consulta do próprio saldo para `customer`;
- negar consulta do saldo de terceiro para `customer`;
- autorizar operação prevista para `manager`;
- negar ação não mapeada para qualquer role;
- validar que o agente não chama MCP após `deny`;
- validar registro de auditoria para `allow` e `deny`.

## 20. Open questions

- `manager` pode operar somente sobre carteira designada ou sobre qualquer cliente
  interno visível no sistema?
- `admin` pode alterar roles diretamente via produto ou isso fica fora do escopo
  do teste?
- a operação de aumento de limite para `customer` deve ser tratada como solicitação
  ou como atualização efetiva do limite?
