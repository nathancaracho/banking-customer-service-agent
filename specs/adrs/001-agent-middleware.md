# ADR 001 - Agent middleware

## Status

Accepted

## Contexto

O `CustomerServiceAgent` precisa aplicar comportamentos transversais sem
espalhar lógica por cada tool:

- autorização antes de tool call;
- human-in-the-loop em operações críticas;
- sanitização e proteção de dados;
- retry, fallback e telemetria no ponto certo do fluxo.

Implementar isso diretamente em cada tool cria duplicação e risco de esquecer
uma proteção quando uma nova tool for adicionada.

## Decisão

Usar middleware do `LangChain` dentro do `CustomerServiceAgent` como ponto
central para interceptar chamadas de modelo e de tools.

O uso inicial obrigatório do middleware será:

- chamar o `Identity` antes de qualquer tool MCP protegida;
- bloquear a execução quando a decisão não for positiva;
- preparar o fluxo de human-in-the-loop para operações críticas.

## Rationale

- mantém a policy fora do modelo e fora das tools individuais;
- reduz duplicação de código de autorização;
- facilita observabilidade e auditoria em um ponto único;
- combina com a arquitetura já definida para workers e checkpoints.

## Consequências

### Positivas

- novas tools entram no fluxo protegido por padrão;
- autorização e HIL ficam explícitos na borda do agent;
- menor risco de bypass acidental em tool sensível.

### Negativas

- introduz uma camada adicional para depuração;
- exige contratos consistentes entre tool, ação, recurso e parâmetros;
- pede testes específicos para middleware.

## Alternativas consideradas

### Autorização em cada tool

Rejeitada porque duplica responsabilidade e aumenta risco de omissão.

### Orquestração totalmente custom sem framework

Rejeitada neste momento porque aumenta custo de implementação do desafio sem
ganho proporcional para o escopo atual.

## Impacto nos projetos

- `agents`
- `identity`
- `backend`

## Specs relacionadas

- [Feature 03](../features/03-credit-limit-increase.md)
- [Feature 05](../features/05-critical-pix.md)
- [Feature 09](../features/09-mcp-tool-contracts.md)
- [Feature 11](../features/11-identity-service.md)
