# Especificações do Agente de Atendimento Bancário Inteligente

## Visão Geral do Escopo

Este repositório contém as especificações técnicas e funcionais para o sistema de Agente de Atendimento Bancário Inteligente. O sistema permite que clientes, gerentes e administradores interajam via chat com um agente capaz de responder dúvidas (RAG), consultar dados, executar operações bancárias e aplicar controle de autorização por perfil.

As specs cobrem exclusivamente as features periféricas e os contratos de integração. A lógica core do agente (orquestração, planner, tool selection interna, pipeline de RAG, guardrails internos) é tratada como caixa-preta e não é detalhada aqui.

## Mapa de Dependências entre Specs

```
01-chat-experience ─────────────────────────────────────────────┐
                                                                 │
02-rag-response-contract ──────── depende de 01 ─────────────────┤
                                                                 │
03-credit-limit-increase ─────── depende de 01, 04, 06, 09 ─────┤
                                                                 │
04-authorization-access-control ─ depende de 06 ────────────────┤
                                                                 │
05-critical-pix ────────────────── depende de 01, 04, 06, 09 ───┤
                                                                 │
06-rbac ────────────────────────── depende de 07 (auditoria) ───┤
                                                                 │
07-audit ───────────────────────── depende de 08 (observabilidade)┤
                                                                 │
08-observability ───────────────── independente ─────────────────┤
                                                                 │
09-mcp-tool-contracts ──────────── depende de 03, 04, 05, 06 ───┤
                                                                 │
10-security-guardrails ─────────── depende de 01 a 09 ───────────┤
```

## Ordem Sugerida de Implementação

| Fase | Specs | Motivo |
|------|-------|--------|
| 1 | 08-observability, 07-audit | Base transversal: métricas e logs precisam existir antes de qualquer feature |
| 2 | 06-rbac, 04-authorization-access-control | Base de autorização: controle de acesso deve estar pronto antes de operações |
| 3 | 01-chat-experience | Canal de interação com o usuário |
| 4 | 02-rag-response-contract | Respostas baseadas em conhecimento |
| 5 | 09-mcp-tool-contracts | Contratos de ferramentas para operações |
| 6 | 03-credit-limit-increase | Operação bancária simples |
| 7 | 05-critical-pix | Operação crítica com autenticação adicional |
| 8 | 10-security-guardrails | Camada final de segurança |

## Riscos Principais

1. **Dependência do core do agente**: As specs assumem interfaces estáveis do agente central. Mudanças no orquestrador interno podem quebrar contratos de fila e checkpoint.
2. **Identity como ponto único de autorização**: Se o Identity falhar, operações protegidas ficam indisponíveis. Estratégia de degradação consciente deve ser definida.
3. **Latência em operações multi-step**: Fluxos com confirmação humana (aumento de limite, PIX) dependem de checkpoint e retomada. Atrasos no consumo da fila podem degradar a experiência.
4. **Consistência entre filas e banco**: Mensagens publicadas na `reply_queue` podem ser perdidas se o backend falhar antes de persistir. O contrato de eventos prevê idempotência via `request_id`.
5. **Vazamento de dados em RAG**: O grounding e a citação de fontes são críticos para evitar alucinações. A política de "não sei" e o limiar de confiança mitigam esse risco.
6. **Autenticação adicional em operações críticas**: O fluxo de step-up authentication adiciona complexidade e atrito. O timeout de confirmação e o cancelamento precisam ser robustos.

## O que foi propositalmente deixado para a "Parte Core"

Os seguintes tópicos **não são especificados** nestes documentos e serão implementados manualmente:

- Orquestração principal do agente (planner, reasoning loop)
- Prompt engineering do agente central
- Estratégia interna de tool selection
- Pipeline interno de RAG (chunking, embedding, ranking detalhado)
- Memória interna do agente
- Implementação do motor de guardrails
- Engine de decisão de risco
- Detalhes internos do workflow engine do agente
- Implementação do compressor de memória (LiteLLM no backend)

## Convenções Adotadas

Baseado no documento `.spec/architecture.md`:

- O backend é a fronteira pública e fonte de verdade dos chats
- O Identity autoriza operações antes da chamada ao MCP
- PostgreSQL é compartilhado fisicamente, separado por schemas (`backend`, `agents`, `identity`)
- Streaming ocorre por chunks (não por token)
- O agente persiste apenas checkpoints
- LiteLLM desacopla os componentes dos provedores de modelo
- O campo `auth_context` não deve aparecer em logs
