# Feature 09 - Contratos de tools MCP

Como produto integrado a sistemas internos, quero contratos claros para as
tools bancárias, para executar consultas e operações com previsibilidade.

Impacta: `backend`, `agents`, `identity`
Stack principal: `LangChain`, `AgentMiddleware`, `MCP`, `RabbitMQ`

## 1. Objetivo

Definir os contratos externos das tools usadas pelo agente para consultar dados e
executar operações bancárias, com foco em previsibilidade, autorização e segurança.

## 2. Escopo

Esta feature cobre:

- catálogo inicial de tools;
- formato lógico de entrada e saída;
- regras de erro;
- relação entre autorização e execução;
- tratamento de operações mutáveis.

## 3. Fora de escopo

Esta feature não cobre:

- implementação interna dos sistemas bancários;
- detalhes do protocolo MCP além do necessário para o contrato de negócio;
- algoritmo interno de escolha de tool pelo agente;
- workflow interno do orquestrador do banco;
- política de versionamento externa do banco.

## 4. Atores envolvidos

- `Customer Service Agent`;
- `identity`;
- servidor MCP;
- sistemas internos bancários;
- backend, como consumidor indireto do resultado.

## 5. Dependências

- autorização prévia via `identity`;
- contexto de requisição com `chat_id` e `request_id`;
- integração entre agent e MCP;
- auditoria de execução de tools.

## 6. Premissas

- tools representam capacidades de negócio observáveis;
- toda tool sensível exige autorização prévia;
- tools mutáveis não devem ser repetidas cegamente após timeout ambíguo;
- `request_id` é a referência de operação do fluxo;
- erros devem ser normalizados para o restante do sistema.

## 7. Fluxo principal

1. O agente identifica que precisa usar uma tool.
2. O agente consulta `identity` com ação e recurso pretendidos.
3. Se a decisão for `allow`, o agente chama a tool no MCP.
4. O MCP retorna sucesso ou erro estruturado.
5. O agente publica a resposta apropriada na reply queue.
6. O backend transmite os chunks e o encerramento ao frontend.

## 8. Fluxos alternativos

- tool de leitura retorna dado consultado e o fluxo segue;
- tool mutável retorna pendência de confirmação e o fluxo entra em HIL;
- tool mutável concluída com sucesso retorna comprovante ou referência de operação.

## 9. Fluxos de erro

- autorização negada impede a chamada ao MCP;
- MCP indisponível retorna erro operacional;
- timeout em operação mutável gera estado inconclusivo;
- argumentos inválidos geram erro validável;
- resposta fora do contrato gera falha tratada e auditável.

## 10. Regras de negócio

- tools iniciais do domínio são:
  - `get_customer_profile`
  - `get_card_limit`
  - `update_card_limit`
  - `create_pix`
- tools de leitura podem adotar retry limitado quando o erro for claramente
  transitório;
- tools mutáveis não devem ser reexecutadas automaticamente após resultado ambíguo;
- o sistema deve usar `request_id` como referência de correlação da operação;
- o agente não deve expor payload bruto interno ao usuário final.

## 11. Requisitos funcionais

- cada tool deve ter contrato de entrada e saída definido;
- o MCP deve retornar status normalizado;
- o agente deve enviar contexto mínimo da requisição;
- operações mutáveis devem retornar referência auditável;
- falhas devem ser classificadas em categoria de negócio, autorização ou
  infraestrutura.

## 12. Requisitos não funcionais

- contratos precisam ser estáveis e versionáveis;
- timeouts devem ser configuráveis;
- validações de entrada devem ocorrer antes de efeitos colaterais;
- erros devem ser previsíveis para facilitar testes;
- integração deve suportar auditoria e observabilidade.

## 13. Contratos / interfaces

Envelope lógico de chamada:

```json
{
  "request_id": "chat_123",
  "chat_id": "chat_123",
  "tool_name": "get_card_limit",
  "actor": {
    "user_id": "usr_123",
    "role": "customer"
  },
  "arguments": {
    "customer_id": "usr_123"
  }
}
```

Resposta lógica:

```json
{
  "status": "success",
  "tool_name": "get_card_limit",
  "data": {
    "customer_id": "usr_123",
    "current_limit": 10000
  },
  "error": null
}
```

Erro lógico:

```json
{
  "status": "error",
  "tool_name": "update_card_limit",
  "data": null,
  "error": {
    "code": "operation_state_unknown",
    "message": "Operation timed out after submission"
  }
}
```

## 14. Modelo de dados necessário

- catálogo de tools permitido por domínio;
- mapeamento entre action de autorização e tool;
- referência de operação por `request_id`;
- registros de execução auditável.

## 15. Eventos e auditoria

- tool solicitada;
- autorização consultada;
- tool iniciada;
- tool concluída com sucesso;
- tool concluída com erro;
- operação mutável em estado inconclusivo.

## 16. Observabilidade

- contagem por tool;
- latência por tool;
- taxa de erro por tool;
- erros de contrato inválido;
- distinção entre falha de autorização, infraestrutura e negócio.

## 17. Segurança e autorização

- nenhuma tool sensível pode ser chamada sem autorização prévia;
- argumentos devem ser validados e sanitizados;
- retorno ao usuário deve ser filtrado para evitar vazamento de detalhe interno;
- payloads críticos devem ser auditados com mascaramento;
- operações mutáveis exigem tratamento mais restritivo que leituras.

## 18. Critérios de aceite

- o sistema executa `get_customer_profile` e `get_card_limit` com contrato estável;
- o sistema executa `update_card_limit` somente após autorização;
- `create_pix` exige fluxo de confirmação adequado antes da efetivação;
- falha de autorização impede a chamada ao MCP;
- timeout ambíguo em operação mutável não dispara retry automático.

## 19. Casos de teste sugeridos

- sucesso em `get_customer_profile`;
- sucesso em `get_card_limit`;
- negativa de autorização antes de `update_card_limit`;
- erro validável para argumento inválido em `create_pix`;
- timeout ambíguo em tool mutável com resposta de estado inconclusivo;
- validação de correlação por `request_id`.

## 20. Open questions

- o desafio precisa de contracts versionados por arquivo ou basta a spec funcional?
- vale expor uma tool de consulta de status de operação para cenários ambíguos?
- `update_card_limit` representa alteração efetiva ou abertura de solicitação de
  mudança de limite no core bancário?
