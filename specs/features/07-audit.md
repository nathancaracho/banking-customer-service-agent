# Feature 07 - Auditoria

Como banco, quero registrar ações relevantes do sistema de forma rastreável,
para investigar incidentes e comprovar decisões críticas.

Domínio principal: `audit`
Projeto principal: `backend`
Impacta: `backend`, `agents`, `identity`
Stack principal: `FastAPI`, `PostgreSQL`, `RabbitMQ`

## 1. Objetivo

Garantir trilha de auditoria confiável para ações relevantes do sistema,
principalmente autorizações, execuções de tools e operações bancárias críticas.

## 2. Escopo

Esta feature cobre:

- eventos auditáveis emitidos por backend, agent e `identity`;
- estrutura mínima dos registros;
- correlação entre requisição, usuário e ação;
- consulta posterior para investigação;
- diferenciação entre auditoria e observabilidade.

## 3. Fora de escopo

Esta feature não cobre:

- SIEM externo;
- retenção legal definitiva;
- trilha de auditoria fora dos componentes do monorepo;
- analytics de produto;
- dashboard completo de investigação.

## 4. Atores envolvidos

- usuário final;
- operador interno;
- time de engenharia;
- time de segurança;
- backend;
- `identity`;
- `Customer Service Agent`.

## 5. Dependências

- autenticação e identificação do usuário;
- geração de `chat_id`, `request_id` e `trace_id`;
- persistência em PostgreSQL;
- contratos de tool e autorização consistentes.

## 6. Premissas

- auditoria não é substituída por logs de aplicação;
- registros precisam sobreviver a falhas do fluxo principal;
- eventos críticos devem ser gravados mesmo em cenários de negação;
- dados sensíveis devem ser minimizados;
- ações críticas precisam ser vinculadas ao ator e ao recurso.

## 7. Fluxo principal

1. O usuário inicia uma interação no chat.
2. O backend cria o contexto da requisição.
3. O agent solicita autorização ao `identity` quando necessário.
4. O sistema registra a decisão de autorização.
5. Se houver execução de tool, o sistema registra a chamada e o resultado.
6. Se houver operação crítica, o sistema registra confirmação e desfecho.
7. Os eventos ficam disponíveis para consulta posterior.

## 8. Fluxos alternativos

- uma ação é negada e ainda assim gera evento de auditoria;
- uma requisição termina antes da tool final, mas os eventos parciais permanecem;
- uma aprovação humana retoma a operação com nova trilha vinculada ao mesmo chat.

## 9. Fluxos de erro

- falha ao gravar auditoria deve gerar alerta operacional;
- campos obrigatórios ausentes invalidam o registro;
- evento sem ator identificado deve ser marcado como inconsistente;
- divergência entre decisão e execução efetiva deve ser tratada como incidente.

## 10. Regras de negócio

- toda ação crítica deve gerar auditoria;
- toda decisão de autorização deve gerar auditoria;
- execução de tool sensível deve ser auditada;
- auditoria deve registrar quem, quando, o quê e com qual resultado;
- payloads sensíveis devem ser mascarados ou referenciados, não copiados integralmente.

## 11. Requisitos funcionais

- o sistema deve persistir eventos de auditoria estruturados;
- deve existir correlação por `chat_id`, `request_id` e `user_id`;
- o registro deve distinguir `allow`, `deny`, `started`, `completed` e `failed`
  quando aplicável;
- auditoria deve cobrir operações críticas de PIX e alterações de limite;
- deve ser possível consultar eventos por período e por ator.

## 12. Requisitos não funcionais

- registros devem ser imutáveis no fluxo normal da aplicação;
- escrita de auditoria deve ter alta confiabilidade;
- esquema precisa ser evolutivo sem quebrar leitura histórica;
- conteúdo auditado deve respeitar minimização de dados;
- acesso à trilha deve ser restrito.

## 13. Contratos / interfaces

Exemplo de evento auditável:

```json
{
  "event_id": "aud_123",
  "event_type": "tool_execution.completed",
  "timestamp": "2026-06-29T10:15:00Z",
  "trace_id": "trc_123",
  "chat_id": "chat_123",
  "request_id": "chat_123",
  "actor": {
    "user_id": "usr_123",
    "role": "customer"
  },
  "action": "pix.create",
  "resource": {
    "type": "bank_account",
    "id": "acc_456"
  },
  "result": "success",
  "metadata": {
    "policy_version": "2026-06-29"
  }
}
```

## 14. Modelo de dados necessário

- `audit_events`;
- índice por `chat_id`;
- índice por `request_id`;
- índice por `user_id`;
- índice por `event_type` e `timestamp`.

## 15. Eventos e auditoria

- `authorization.decided`;
- `tool_execution.started`;
- `tool_execution.completed`;
- `tool_execution.failed`;
- `critical_operation.confirmation_requested`;
- `critical_operation.confirmed`;
- `critical_operation.completed`;
- `critical_operation.denied`.

## 16. Observabilidade

- taxa de falha de gravação de auditoria;
- volume de eventos por tipo;
- defasagem entre evento de negócio e persistência;
- correlação de eventos críticos com traces operacionais;
- alerta para ausência inesperada de auditoria em operações críticas.

## 17. Segurança e autorização

- somente componentes autorizados podem gravar eventos;
- acesso de leitura à trilha deve ser restrito;
- campos com PII devem ser minimizados ou mascarados;
- segredos, prompts internos e texto integral sensível não devem ser auditados;
- operações de leitura da trilha também podem ser auditadas.

## 18. Critérios de aceite

- toda tentativa de operação crítica gera trilha auditável;
- toda decisão `allow` ou `deny` de autorização gera trilha;
- a trilha permite correlacionar usuário, chat, ação e resultado;
- payload sensível não aparece em claro nos registros;
- falhas de persistência geram sinal operacional detectável.

## 19. Casos de teste sugeridos

- registrar auditoria em consulta autorizada;
- registrar auditoria em consulta negada;
- registrar fluxo completo de `pix.create` com confirmação;
- validar mascaramento de campos sensíveis;
- validar busca por `chat_id`;
- validar ausência de duplicação indevida para o mesmo evento.

## 20. Open questions

- qual é a política de retenção mínima esperada para o teste?
- o desafio exige tela de consulta de auditoria ou basta persistência e evidência
  técnica?
- a confirmação humana deve gerar um evento próprio ou reaproveitar o mesmo tipo
  de evento com status diferente?
