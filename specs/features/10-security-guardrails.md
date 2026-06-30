# Feature 10 - Segurança e guardrails

Como banco, quero cercar o agente com proteções explícitas, para bloquear usos
indevidos, reduzir vazamentos e garantir execução segura.

Domínio principal: `security`
Projeto principal: `agents`
Impacta: `frontend`, `backend`, `agents`, `identity`
Stack principal: `FastAPI`, `LangChain`, `AgentMiddleware`, `PostgreSQL`

## 1. Objetivo

Definir os mecanismos de proteção do produto em torno do agente para reduzir risco
de acesso indevido, execução insegura e vazamento de dados.

## 2. Escopo

Esta feature cobre:

- validação de autenticação e autorização;
- tratamento de entrada não confiável;
- proteção em tool calling;
- confirmação para operações sensíveis;
- minimização de exposição de dados.

## 3. Fora de escopo

Esta feature não cobre:

- implementação detalhada de um guardrail engine dedicado;
- modelagem antifraude avançada;
- WAF, CDN ou segurança perimetral completa;
- hardening de sistema operacional;
- política jurídica ou regulatória formal.

## 4. Atores envolvidos

- usuário final;
- operador interno;
- frontend;
- backend;
- `Customer Service Agent`;
- `identity`;
- MCP e sistemas internos.

## 5. Dependências

- autenticação válida;
- RBAC definido;
- contratos de tools;
- auditoria;
- observabilidade.

## 6. Premissas

- entrada do usuário é não confiável por definição;
- conteúdo de documentos da KB também é não confiável;
- resposta de tools externas deve ser tratada como dado não confiável até validação;
- autorização e validação de negócio devem acontecer fora do modelo;
- operações críticas exigem barreiras adicionais.

## 7. Fluxo principal

1. O usuário envia uma solicitação.
2. O backend valida autenticação e contexto.
3. O agente processa a solicitação e, se precisar de tool, consulta `identity`.
4. O sistema valida se a ação é permitida.
5. Se a ação for sensível, o sistema exige confirmação explícita.
6. A tool é executada somente após as validações necessárias.
7. O resultado é sanitizado antes de voltar ao usuário.

## 8. Fluxos alternativos

- pergunta informacional segue sem tool mutável;
- consulta RAG usa apenas documentos permitidos pela política;
- operação crítica pausa para confirmação humana e depois retoma.

## 9. Fluxos de erro

- prompt injection tenta induzir o agente a ignorar policy;
- usuário tenta acessar dado de terceiro;
- MCP retorna dado inesperado ou excessivo;
- token inválido chega ao backend;
- operação sensível é enviada sem confirmação necessária.

## 10. Regras de negócio

- o modelo não decide autorização sozinho;
- instruções vindas de usuário, KB ou tool não podem substituir policy do sistema;
- confirmação explícita é obrigatória para operação crítica;
- respostas ao usuário devem conter apenas o mínimo necessário;
- falha de segurança deve resultar em bloqueio seguro.

## 11. Requisitos funcionais

- o sistema deve validar autenticação antes do fluxo de chat;
- o sistema deve consultar `identity` antes de tool sensível;
- o sistema deve bloquear tool call quando a autorização for negada;
- o sistema deve exigir confirmação para operações críticas;
- o sistema deve sanitizar mensagens, logs e auditoria para evitar vazamento.

## 12. Requisitos não funcionais

- falhas devem degradar para modo seguro;
- a estratégia de proteção deve ser explicável aos avaliadores;
- a superfície exposta pelo agente deve ser mínima;
- mecanismos de proteção devem ser testáveis;
- componentes devem manter separação de responsabilidades.

## 13. Contratos / interfaces

Exemplo de resultado lógico de proteção:

```json
{
  "status": "blocked",
  "reason": "authorization_denied",
  "action": "pix.create",
  "chat_id": "chat_123",
  "request_id": "chat_123"
}
```

Exemplo de confirmação requerida:

```json
{
  "status": "confirmation_required",
  "action": "pix.create",
  "details": {
    "amount": 20000,
    "target": "dest_123"
  }
}
```

## 14. Modelo de dados necessário

- políticas e permissões no schema de `identity`;
- vínculo entre usuário e role;
- eventos de auditoria;
- checkpoints para retomada segura após confirmação.

## 15. Eventos e auditoria

- tentativa de acesso negado;
- confirmação requerida;
- confirmação recebida;
- tool bloqueada por policy;
- operação crítica efetivada;
- resposta descartada por violação de contrato.

## 16. Observabilidade

- taxa de bloqueios de autorização;
- taxa de confirmações exigidas;
- tentativas de acesso indevido;
- erros de validação de contrato de tool;
- traces de fluxos críticos com decisão de segurança.

## 17. Segurança e autorização

- autenticação validada no backend;
- autorização validada no `identity`;
- tool calling protegido por policy explícita;
- dados sensíveis mascarados em logs e auditoria;
- prompts, documentos e respostas externas tratados como entrada não confiável.

## 18. Critérios de aceite

- o sistema bloqueia acesso a dado não autorizado;
- o sistema não executa tool sensível sem validação prévia;
- operações críticas exigem confirmação explícita;
- falha em dependência de segurança resulta em bloqueio e não em liberação;
- a demo consegue explicar claramente as barreiras de proteção.

## 19. Casos de teste sugeridos

- negar consulta de saldo de terceiro para `customer`;
- bloquear `create_pix` sem confirmação;
- bloquear tool call após falha do `identity`;
- validar sanitização de resposta de tool com excesso de dados;
- validar auditoria de tentativa negada;
- validar retomada segura após confirmação humana.

## 20. Open questions

- o escopo do teste pede MFA real ou basta confirmação explícita no fluxo?
- vale incluir rate limiting como requisito visível da demo ou isso adiciona ruído
  desnecessário?
- quais campos de payload bancário precisam de mascaramento obrigatório na entrega
  final?
