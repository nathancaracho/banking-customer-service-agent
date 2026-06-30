# Feature 03 — Aumento de limite de cartão

Como usuário elegível, quero solicitar aumento de limite com transparência,
confirmação e segurança, para concluir a operação com confiança.

Impacta: `frontend`, `backend`, `agents`, `identity`
Stack principal: `FastAPI`, `LangChain`, `AgentMiddleware`, `RabbitMQ`, `MCP`

## 1. Objetivo

Permitir que um usuário elegível solicite e confirme o aumento do limite de seu
cartão antes da execução da operação.

## 2. Escopo

- consulta de perfil, limite atual e elegibilidade pelo `CustomerServiceAgent`;
- apresentação das condições;
- confirmação explícita;
- execução por MCP;
- resposta final e auditoria.

## 3. Fora de escopo

- algoritmo de elegibilidade;
- reasoning loop e seleção interna de ferramentas;
- definição comercial de limites máximos;
- interface visual detalhada da confirmação.

## 4. Atores envolvidos

- customer, manager ou admin;
- frontend e backend;
- `CustomerServiceAgent`;
- Identity;
- MCP;
- sistema de cartões.

## 5. Dependências

- chat e checkpoint;
- RBAC e controle de acesso;
- contratos MCP;
- auditoria, observabilidade e segurança.

## 6. Premissas

- o perfil e a elegibilidade vêm de sistemas internos;
- o backend não consulta limite ou elegibilidade diretamente no sistema bancário;
- a confirmação é vinculada ao valor e ao cartão apresentados;
- o worker encerra após solicitar confirmação;
- o usuário deve estar autorizado para o cartão alvo.

## 7. Fluxo principal

1. O usuário solicita um novo limite.
2. O agente identifica o cartão e o valor desejado.
3. O Identity autoriza a consulta e a intenção de alteração.
4. O agente consulta perfil, limite atual e elegibilidade pelo MCP.
5. O agente apresenta limite atual, novo limite e condições.
6. O usuário confirma explicitamente.
7. Uma nova execução retoma o checkpoint e revalida a autorização.
8. O agente executa a alteração pelo MCP.
9. O backend persiste a resposta final.

## 8. Fluxos alternativos

- Valor ausente: solicitar o valor desejado.
- Mais de um cartão: solicitar seleção.
- Usuário inelegível: explicar a impossibilidade sem expor regras internas.
- Valor parcialmente elegível: oferecer o máximo retornado pelo sistema.
- Usuário cancela: encerrar sem executar a alteração.

## 9. Fluxos de erro

- Perfil ou cartão não encontrado: retornar erro seguro.
- Identity nega: não consultar ou alterar dados.
- Sistema de cartões indisponível: informar falha temporária.
- Confirmação expirada: gerar uma nova proposta.
- Resultado da mutação incerto: não repetir automaticamente; consultar o estado
  atual antes de orientar nova tentativa.

## 10. Regras de negócio

- Nenhuma alteração ocorre sem autorização e confirmação.
- O `CustomerServiceAgent` é o responsável por consultar perfil, limite atual e
  elegibilidade antes da mutação.
- O backend não executa consulta de limite nem mutação bancária.
- A confirmação vale apenas para os parâmetros apresentados.
- Alteração de cartão, valor ou condições invalida a confirmação.
- Elegibilidade é determinada pelo sistema interno, não pelo modelo.
- A autorização deve ser refeita antes da mutação.

## 11. Requisitos funcionais

- RF-01: o `CustomerServiceAgent` deve consultar perfil e limite atual.
- RF-02: verificar elegibilidade para o valor solicitado.
- RF-03: solicitar confirmação explícita.
- RF-04: retomar a execução por checkpoint.
- RF-05: executar a alteração somente após revalidação.
- RF-06: informar o novo limite confirmado pelo sistema.

## 12. Requisitos não funcionais

- O worker não pode permanecer bloqueado aguardando confirmação.
- A operação deve ser rastreável por `request_id` e `chat_id`.
- Falhas ambíguas não podem causar repetição automática da mutação.

## 13. Contratos / interfaces

Pedido de confirmação:

```json
{
  "type": "confirmation_required",
  "payload": {
    "operation": "increase_credit_limit",
    "card_reference": "masked-card-reference",
    "current_limit": 10000,
    "requested_limit": 15000,
    "currency": "BRL"
  }
}
```

Resultado:

```json
{
  "status": "completed",
  "previous_limit": 10000,
  "current_limit": 15000,
  "currency": "BRL"
}
```

## 14. Modelo de dados necessário

- `AgentCheckpoint`: estado e parâmetros da operação pendente.
- `Confirmation`: usuário, operação, parâmetros, expiração e decisão.
- Registros bancários permanecem no sistema interno, não no banco do agente.

## 15. Eventos e auditoria

- `credit_limit.requested`;
- `credit_limit.eligibility_checked`;
- `credit_limit.confirmation_requested`;
- `credit_limit.confirmed` ou `credit_limit.cancelled`;
- `credit_limit.executed` ou `credit_limit.failed`.

## 16. Observabilidade

- duração por etapa;
- taxa de elegibilidade;
- confirmações, cancelamentos e expirações;
- falhas por ferramenta;
- operações com resultado incerto.

## 17. Segurança e autorização

- Mascarar referência do cartão.
- Não expor score, regras internas ou dados completos do perfil.
- Vincular confirmação ao usuário autenticado.
- Revalidar Identity antes de consultar e antes de alterar.

## 18. Critérios de aceite

- Um usuário elegível consegue confirmar e concluir a alteração.
- Usuário inelegível não executa a ferramenta de mutação.
- Cancelamento e expiração não alteram o limite.
- Mudança de valor exige nova confirmação.
- A trilha de auditoria reconstrói todas as etapas.

## 19. Casos de teste sugeridos

- aumento elegível confirmado;
- aumento inelegível;
- valor ausente;
- múltiplos cartões;
- confirmação cancelada ou expirada;
- autorização revogada entre confirmação e execução;
- timeout com resultado da mutação desconhecido.

## 20. Open questions

- Customer pode alterar o próprio limite ou apenas solicitar aprovação?
- Qual é a validade da confirmação?
- Qual ferramenta determina elegibilidade?
- Qual comportamento esperado quando o sistema retorna um limite alternativo?
