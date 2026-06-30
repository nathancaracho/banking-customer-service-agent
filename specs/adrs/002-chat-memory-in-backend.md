# ADR 002 - Chat memory in backend

## Status

Accepted

## Contexto

O sistema precisa manter conversas longas, resolver referências elípticas e
suportar streaming assíncrono para muitos usuários sem acoplar o histórico do
chat ao estado interno do worker.

Também existe a necessidade de pausar execuções em HIL sem manter um worker
bloqueado por conversa.

## Decisão

O backend será a fonte de verdade da memória do chat.

Isso implica:

- persistir mensagens e respostas finais no backend;
- gerar e atualizar o `summary` no backend;
- enviar ao agent apenas `summary`, mensagens recentes e mensagem atual;
- manter no agent apenas checkpoint técnico de execução, nunca o histórico
  oficial do chat.

## Rationale

- separa claramente memória conversacional de estado técnico do agent;
- permite escalar workers horizontalmente sem carregar histórico completo;
- facilita retry, reconexão SSE e persistência do chat;
- evita tratar o banco vetorial como repositório do histórico do usuário.

## Consequências

### Positivas

- agentes podem ser mais stateless;
- compressão de memória fica centralizada no backend;
- o histórico oficial do usuário não depende do framework do agent.

### Negativas

- o backend assume responsabilidade maior;
- exige contrato claro entre backend e agent para memória resumida;
- a qualidade do `summary` vira parte crítica do sistema.

## Alternativas consideradas

### Memória no próprio agent

Rejeitada porque mistura estado de execução com histórico do usuário e dificulta
escala independente dos workers.

### Indexar o chat inteiro em vector database

Rejeitada porque o chat do usuário não é a KB do produto e porque isso adiciona
complexidade desnecessária ao caso de uso atual.

## Impacto nos projetos

- `backend`
- `agents`

## Specs relacionadas

- [Feature 01](../features/01-chat-experience.md)
- [Feature 02](../features/02-rag-response-contract.md)
- [Feature 08](../features/08-observability.md)
