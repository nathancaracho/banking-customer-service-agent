# Agents

Worker do `CustomerServiceAgent` responsável por:

- consumir a fila `agent.requests`;
- consultar a base de conhecimento no Chroma;
- autorizar tool calls no `identity`;
- executar tools pelo `mcp_proxy`;
- publicar `chunk`, `completed` ou `failed` em `agent.replies`.

## Fluxos implementados

- consulta de saldo;
- consulta de limite;
- proposta e confirmação conversacional de aumento de limite;
- proposta e confirmação conversacional de PIX;
- fallback RAG com citações simples da KB.

## Limites atuais

- confirmação ainda é conversacional; não há checkpoint técnico persistido;
- PIX ainda não exige autenticação adicional;
- elegibilidade de limite está básica e local ao agent;
- observabilidade e auditoria do worker ainda precisam ser expandidas.
