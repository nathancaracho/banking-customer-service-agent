# Feature 05 — Operação crítica PIX

Como usuário autenticado, quero realizar uma transferência PIX crítica com
validações e confirmação reforçadas, para executar a operação com segurança.

Impacta: `frontend`, `backend`, `agents`, `identity`
Stack principal: `FastAPI`, `LangChain`, `AgentMiddleware`, `RabbitMQ`, `MCP`

## 1. Objetivo

Executar transferências PIX críticas somente após autorização, autenticação
adicional, validações bancárias e confirmação explícita.

## 2. Escopo

- coleta dos dados da transferência;
- autorização e avaliação externa de risco;
- autenticação adicional;
- validação de saldo e limites;
- confirmação, execução, cancelamento e auditoria reforçada.

## 3. Fora de escopo

- implementação do motor de risco;
- mecanismo interno da autenticação adicional;
- liquidação e antifraude bancários;
- reasoning loop do agente.

## 4. Atores envolvidos

- usuário autenticado;
- frontend e backend;
- `CustomerServiceAgent`;
- Identity;
- MCP;
- sistemas PIX, risco e autenticação.

## 5. Dependências

- chat, checkpoint e confirmação;
- RBAC e controle de acesso;
- contratos MCP;
- auditoria, observabilidade e segurança.

## 6. Premissas

- o sistema interno classifica a operação como crítica;
- autenticação adicional produz evidência verificável e expira;
- o destinatário e o valor apresentados são os executados;
- o worker não aguarda o usuário em memória.

## 7. Fluxo principal

1. O usuário informa destinatário e valor.
2. O agente valida os campos e solicita autorização ao Identity.
3. Ferramentas internas verificam risco, saldo e limites.
4. O sistema solicita autenticação adicional.
5. Após sucesso, o agente apresenta o resumo completo e pede confirmação.
6. O agente salva checkpoint e encerra a execução.
7. Uma nova solicitação recebe a confirmação, retoma e revalida o contexto.
8. O MCP executa o PIX.
9. O agente retorna o status confirmado pelo sistema.

## 8. Fluxos alternativos

- Dados incompletos: solicitar somente os campos ausentes.
- Usuário cancela: encerrar sem executar.
- Autenticação expira: solicitar uma nova autenticação.
- Risco ou limite bloqueia: negar a operação com mensagem segura.
- PIX fica pendente: informar status pendente e referência da operação.

## 9. Fluxos de erro

- Saldo insuficiente: não solicitar confirmação de execução.
- Chave inválida: solicitar correção.
- Autenticação adicional falha: negar.
- Confirmação diverge dos parâmetros: invalidar.
- Timeout antes da mutação: informar falha recuperável.
- Timeout após envio ao sistema PIX: consultar status; não repetir
  automaticamente.

## 10. Regras de negócio

- PIX crítico exige autenticação adicional e confirmação explícita.
- Confirmação é vinculada a origem, destino, valor e moeda.
- Qualquer alteração invalida autenticação e confirmação anteriores.
- Risco, saldo e limites são definidos pelos sistemas internos.
- A resposta final não pode afirmar sucesso sem confirmação do sistema PIX.

## 11. Requisitos funcionais

- RF-01: validar os dados obrigatórios.
- RF-02: autorizar e verificar risco, saldo e limites.
- RF-03: exigir autenticação adicional.
- RF-04: apresentar resumo e obter confirmação.
- RF-05: retomar o checkpoint sem bloquear worker.
- RF-06: executar e retornar status confiável.
- RF-07: permitir cancelamento ou abandono.

## 12. Requisitos não funcionais

- Toda etapa deve ser rastreável.
- Dados sensíveis devem ser mascarados.
- Falhas ambíguas não podem provocar repetição automática.
- Confirmações e autenticações devem expirar.

## 13. Contratos / interfaces

Confirmação:

```json
{
  "type": "confirmation_required",
  "payload": {
    "operation": "create_pix",
    "destination": "***1234",
    "amount": 20000,
    "currency": "BRL",
    "additional_auth": "verified"
  }
}
```

Resultado:

```json
{
  "status": "completed",
  "transaction_reference": "masked-reference",
  "amount": 20000,
  "currency": "BRL"
}
```

## 14. Modelo de dados necessário

- `AgentCheckpoint`;
- `AdditionalAuthEvidence`;
- `Confirmation`;
- referência externa da transação.

Dados financeiros oficiais permanecem nos sistemas bancários.

## 15. Eventos e auditoria

- `pix.requested`;
- `pix.risk_checked`;
- `pix.additional_auth_requested`;
- `pix.additional_auth_succeeded` ou `failed`;
- `pix.confirmed`, `cancelled` ou `expired`;
- `pix.execution_requested`;
- `pix.completed`, `pending` ou `failed`.

## 16. Observabilidade

- duração por etapa;
- falhas de autenticação;
- bloqueios por risco, saldo e limite;
- confirmações expiradas;
- PIX pendentes;
- resultados ambíguos e consultas de status.

## 17. Segurança e autorização

- Não registrar chave, conta, token ou evidência completa.
- Vincular autenticação e confirmação ao usuário e à operação.
- Revalidar Identity imediatamente antes da execução.
- Falhar fechado quando risco, Identity ou autenticação estiverem indisponíveis.

## 18. Critérios de aceite

- PIX crítico nunca é executado sem autenticação e confirmação válidas.
- Cancelamento, expiração ou divergência impedem a execução.
- Timeout ambíguo não gera uma segunda transferência.
- O usuário recebe somente status confirmado ou explicitamente pendente.
- A auditoria reconstrói todas as decisões.

## 19. Casos de teste sugeridos

- fluxo completo aprovado;
- saldo insuficiente;
- limite excedido;
- risco bloqueado;
- autenticação falha ou expira;
- usuário cancela;
- parâmetros alterados após confirmação;
- timeout antes e depois do envio ao PIX.

## 20. Open questions

- Qual valor ou regra torna o PIX crítico?
- Qual mecanismo implementa autenticação adicional?
- Qual é a validade da autenticação e da confirmação?
- Existe ferramenta de consulta de status da transferência?
