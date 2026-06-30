# Feature 04 — Autorização e acesso a dados

Como cliente ou colaborador autorizado, quero acessar somente os dados e
operações compatíveis com meu perfil, para proteger informações sensíveis.

Domínio principal: `authorization`
Projeto principal: `identity`
Impacta: `backend`, `agents`, `identity`
Stack principal: `FastAPI`, `AgentMiddleware`, `PostgreSQL`, `MCP`

## 1. Objetivo

Impedir acesso indevido a dados e operações, aplicando autorização no Identity
antes de qualquer ferramenta protegida.

## 2. Escopo

- acesso a dados próprios e de terceiros;
- contrato de decisão do Identity;
- mensagens seguras de negação;
- revalidação para operações sensíveis;
- auditoria de decisões.

## 3. Fora de escopo

- implementação interna do policy engine;
- autenticação e emissão de tokens;
- gestão visual de roles;
- regras internas de risco.

## 4. Atores envolvidos

- customer, manager e admin;
- backend;
- `CustomerServiceAgent`;
- Identity;
- MCP e sistemas internos.

## 5. Dependências

- contexto de autenticação válido;
- RBAC;
- contratos MCP;
- auditoria e observabilidade.

## 6. Premissas

- o Identity é a fonte de verdade para roles e permissões;
- o modelo nunca concede autorização;
- o recurso alvo é resolvido antes da decisão;
- uma decisão vale apenas para a ação e os parâmetros avaliados.

## 7. Fluxo principal

1. O agente identifica a ação e o recurso solicitados.
2. O agente envia o contexto ao Identity.
3. O Identity identifica usuário, roles e relação com o recurso.
4. O Identity retorna `authorized`.
5. O agente executa a ferramenta autorizada.
6. A decisão e o resultado são auditados.

## 8. Fluxos alternativos

- Acesso a dado próprio: aplicar permissão de proprietário.
- Acesso de manager a terceiro: exigir permissão e contexto permitido.
- Admin: aplicar permissão administrativa explícita, sem bypass implícito.
- Recurso ambíguo: solicitar esclarecimento antes da autorização.

## 9. Fluxos de erro

- Token inválido ou expirado: negar e solicitar nova autenticação.
- Recurso inexistente: retornar mensagem que não permita enumeração.
- Permissão ausente: negar sem chamar MCP.
- Identity indisponível: falhar fechado.
- Parâmetros alterados após autorização: invalidar a decisão.

## 10. Regras de negócio

- Customer acessa apenas os próprios dados.
- Acesso a terceiros exige permissão explícita.
- Admin não ignora políticas; possui permissões declaradas.
- Toda negação ocorre antes da chamada protegida.
- Falha de autorização nunca vira autorização por fallback.

## 11. Requisitos funcionais

- RF-01: autorizar por usuário, role, ação, recurso e parâmetros.
- RF-02: diferenciar dados próprios de terceiros.
- RF-03: impedir execução quando a decisão não for positiva.
- RF-04: retornar mensagem segura de negação.
- RF-05: auditar autorizações e negações.

## 12. Requisitos não funcionais

- Decisões devem ser determinísticas para a mesma política e contexto.
- A autorização deve ocorrer dentro do timeout da operação.
- Alterações de políticas devem valer sem modificar o agente.

## 13. Contratos / interfaces

```json
{
  "subject": {"user_id": "uuid", "roles": ["customer"]},
  "action": "account.balance.read",
  "resource": {"type": "account", "owner_id": "uuid"},
  "context": {"request_id": "uuid"}
}
```

```json
{
  "decision": "denied",
  "reason_code": "RESOURCE_NOT_OWNED",
  "policy_version": "2026-06-01"
}
```

`reason_code` é interno e não precisa ser exibido ao usuário.

## 14. Modelo de dados necessário

- `User`;
- `Role`;
- `Permission`;
- `RolePermission`;
- `AuthorizationDecision` para auditoria.

## 15. Eventos e auditoria

- `authorization.allowed`;
- `authorization.denied`;
- `authorization.error`;
- `protected_tool.blocked`.

Registrar política, ação e recurso mascarado, sem registrar tokens.

## 16. Observabilidade

- latência do Identity;
- decisões por ação e resultado;
- falhas fechadas;
- tentativas de acesso a terceiros;
- ferramentas bloqueadas.

## 17. Segurança e autorização

- Validar o token, não confiar apenas no `user_id` do payload.
- Não expor existência, saldo ou identificadores de recurso negado.
- Aplicar least privilege.
- Revalidar operações após confirmação humana.

## 18. Critérios de aceite

- Customer consulta o próprio saldo.
- Customer não consulta saldo de terceiro.
- Manager/admin só acessam terceiro quando a permissão existir.
- Identity indisponível impede a ferramenta.
- A negação aparece na auditoria sem vazar dados.

## 19. Casos de teste sugeridos

- dado próprio autorizado;
- terceiro negado para customer;
- terceiro autorizado para role permitida;
- token expirado;
- Identity indisponível;
- recurso inexistente;
- alteração de parâmetros após autorização.

## 20. Open questions

- Manager precisa informar justificativa para acessar terceiros?
- Quais recursos um admin pode acessar?
- As roles vêm somente do token ou são sempre consultadas no banco?
