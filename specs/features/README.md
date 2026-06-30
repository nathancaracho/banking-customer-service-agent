# Specs de features

## Escopo

Estas specs descrevem o comportamento externo e as integrações das features do
Agente de Atendimento Bancário Inteligente. A implementação interna do
`CustomerServiceAgent` permanece intencionalmente como uma caixa-preta.

Complementos técnicos:

- [Stack técnica](../tech-stack.md)
- [ADR 001 — Agent middleware](../adrs/001-agent-middleware.md)
- [ADR 002 — Chat memory in backend](../adrs/002-chat-memory-in-backend.md)
- [ADR 003 — Identity before tool call](../adrs/003-identity-before-tool-call.md)

As fontes canônicas utilizadas foram:

- [`AGENTS.md`](../../AGENTS.md);
- [`specs/architecture.md`](../architecture.md).

O prompt de geração citava `agent.md` e `.specs/architecture.md`. Este
repositório adota `AGENTS.md` e `specs/architecture.md` como referências
canônicas.

## Índice

| Spec | Domínio principal | Projeto principal | Responsabilidade principal |
| --- | --- | --- | --- |
| [01 — Experiência do chat](01-chat-experience.md) | Chat | `backend` | Chat, memória, SSE e estados da interface |
| [02 — Resposta RAG](02-rag-response-contract.md) | RAG | `agents` | Resposta fundamentada e citações |
| [03 — Aumento de limite](03-credit-limit-increase.md) | Cartão | `agents` | Fluxo de consulta, elegibilidade, confirmação e execução |
| [04 — Controle de acesso](04-authorization-access-control.md) | Autorização | `identity` | Autorização de dados próprios e de terceiros |
| [05 — PIX crítico](05-critical-pix.md) | PIX | `agents` | Autenticação adicional, confirmação e execução |
| [06 — RBAC](06-rbac.md) | Permissões | `identity` | Perfis e matriz de permissões |
| [07 — Auditoria](07-audit.md) | Auditoria | `backend` | Eventos auditáveis e trilha de ações |
| [08 — Observabilidade](08-observability.md) | Observabilidade | `backend` | Logs, métricas, traces e alertas |
| [09 — Contratos MCP](09-mcp-tool-contracts.md) | Integração | `agents` | Interfaces externas das ferramentas |
| [10 — Segurança](10-security-guardrails.md) | Segurança | `agents` | Guardrails visíveis nas bordas do sistema |
| [11 — Identity](11-identity-service.md) | Identidade | `identity` | Validação de contexto, resolução de roles e decisão de autorização |
| [12 — Ingestion e gestão da KB](12-file-ingestion.md) | Base de conhecimento | `backend` | Upload, parsing, indexação, ativação e ciclo de vida dos documentos da KB |

## Dependências

```text
01 Chat ───────────────┬──> 02 RAG
                      ├──> 03 Aumento de limite
                      └──> 05 PIX crítico

12 Ingestion + Gestão KB ──> 02 RAG

11 Identity ──────────┬──> 04 Controle de acesso
                      ├──> 12 Ingestion + Gestão KB
06 RBAC ──────────────└──> 04 Controle de acesso

04 Controle de acesso ─┬──> 03 Aumento de limite ──> 09 MCP
09 Contratos MCP ──────┘

04 Controle de acesso ─┬──> 05 PIX crítico ────────> 09 MCP
09 Contratos MCP ──────┘

Todas as features ───────> 07 Auditoria
Todas as features ───────> 08 Observabilidade
Todas as features ───────> 10 Segurança
```

## Ordem sugerida de implementação

1. Identity e RBAC.
2. Controle de acesso e contratos MCP.
3. Ingestion e gestão da KB.
4. Auditoria e observabilidade.
5. Chat e streaming.
6. Resposta RAG.
7. Aumento de limite.
8. PIX crítico.
9. Guardrails e testes transversais.

## Convenções compartilhadas

- `chat_id` identifica o chat.
- `request_id` identifica uma execução dentro do chat.
- `sequence` é numérico, inicia em `1` e ordena eventos da resposta.
- O backend é a fonte de verdade do chat e da memória conversacional.
- O agente recebe `summary`, mensagens recentes e a mensagem atual.
- O agente publica `chunk`, `confirmation_required`, `completed` ou `failed`.
- O Identity é consultado antes de qualquer ferramenta protegida.
- Interações humanas pausam a execução por checkpoint; nenhum worker fica
  bloqueado aguardando o usuário.
- O streaming interno publica chunks, não tokens individuais.

## Riscos principais

- autorização baseada em dados fornecidos pelo modelo;
- repetição de efeitos após falhas ambíguas em ferramentas de mutação;
- vazamento de dados em respostas, logs, traces ou prompts;
- perda de contexto após compressão inadequada do chat;
- divergência entre a confirmação apresentada e os parâmetros executados;
- ausência de thresholds definidos para confiança, risco, timeout e alertas.

## Parte core deixada de fora

- prompt e reasoning loop do agente;
- planejamento e seleção interna de ferramentas;
- pipeline de chunking, embedding, retrieval e ranking;
- algoritmo de compressão da memória;
- engine de guardrails;
- engine de risco;
- implementação interna do workflow e dos checkpoints.

Esses componentes são tratados como caixas-pretas com interfaces e resultados
observáveis definidos nas specs.
