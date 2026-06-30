# ADR 003 - Identity before tool call

## Status

Accepted

## Contexto

O agente acessa tools que podem consultar dados bancários e executar operações
sensíveis. Nesse cenário, não é aceitável depender apenas da intenção inferida
pelo modelo para liberar uma chamada protegida.

Além disso, o backend já precisa validar o contexto de autenticação antes de
abrir o fluxo de chat.

## Decisão

Toda tool MCP protegida será precedida por uma decisão do `Identity`.

O fluxo adotado é:

1. `backend.auth` valida o contexto de autenticação com o `Identity`;
2. o `CustomerServiceAgent`, via middleware, chama o `Identity` antes de tool
   call protegida;
3. somente com decisão positiva a tool é executada.

## Rationale

- centraliza autorização em um serviço único;
- reduz risco de vazamento e mutação indevida;
- permite evolução de policy sem reescrever o agent;
- melhora auditabilidade e explicação da arquitetura na entrevista.

## Consequências

### Positivas

- policy fica desacoplada do modelo e das tools;
- falhas fechadas ficam explícitas;
- novas tools entram mais facilmente em um fluxo seguro.

### Negativas

- adiciona latência por decisão;
- exige mapear `tool_name` para `action` e `resource`;
- requer boa observabilidade do `Identity`.

## Alternativas consideradas

### Confiar na role já resolvida no início do chat

Rejeitada porque não basta para autorizar cada ação e cada recurso alvo.

### Chamar MCP e filtrar depois

Rejeitada porque permitiria acesso indevido antes do bloqueio.

## Impacto nos projetos

- `backend`
- `agents`
- `identity`

## Specs relacionadas

- [Feature 04](../features/04-authorization-access-control.md)
- [Feature 05](../features/05-critical-pix.md)
- [Feature 06](../features/06-rbac.md)
- [Feature 09](../features/09-mcp-tool-contracts.md)
- [Feature 11](../features/11-identity-service.md)
