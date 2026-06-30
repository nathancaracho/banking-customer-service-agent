# Feature 13 — Gestão da base de conhecimento

Como responsável pela KB, quero listar, ativar, desativar, reprocessar e remover
documentos ingeridos, para manter a base usada pelo agente confiável e atual.

Impacta: `frontend`, `backend`, `identity`, `agents`
Stack principal: `React`, `FastAPI`, `PostgreSQL`, `Chroma`

## 1. Objetivo

Permitir o gerenciamento operacional dos documentos já ingeridos na base de
conhecimento, controlando status, versões e disponibilidade para o fluxo de
RAG.

## 2. Escopo

- listagem de documentos ingeridos;
- exibição de status, versão, origem e metadados principais;
- ativação e desativação de documentos;
- reprocessamento de documento existente;
- remoção lógica ou física de documento, conforme política adotada;
- visibilidade de impacto sobre a coleção usada pelo RAG.

## 3. Fora de escopo

- edição inline do conteúdo chunkado;
- curadoria semântica automática;
- workflow editorial complexo com múltiplos aprovadores;
- dashboard analítico avançado de uso por documento;
- reescrita manual de chunks individuais.

## 4. Atores envolvidos

- usuário administrativo autorizado;
- frontend;
- backend;
- `Identity`;
- `Chroma`;
- `CustomerServiceAgent` como consumidor da versão ativa da KB.

## 5. Dependências

- Feature 06 - RBAC;
- Feature 07 - Auditoria;
- Feature 08 - Observabilidade;
- Feature 10 - Segurança e guardrails;
- Feature 11 - Identity service;
- Feature 12 - File ingestion.

## 6. Premissas

- o gerenciamento da KB acontece no backend;
- o agent consome apenas documentos ativos;
- reprocessar um documento pode criar uma nova versão;
- operações administrativas exigem permissão explícita;
- o estado da KB precisa ser consistente entre banco e `Chroma`.

## 7. Fluxo principal

1. O usuário acessa a tela de gestão da KB.
2. O frontend solicita a lista de documentos ao backend.
3. O backend valida autenticação e permissão no `Identity`.
4. O backend retorna documentos, versões e status.
5. O usuário seleciona uma ação administrativa.
6. O backend aplica a ação solicitada.
7. O backend sincroniza metadados e índice vetorial quando necessário.
8. O frontend exibe o novo estado do documento.

## 8. Fluxos alternativos

- ativar um documento previamente ingerido;
- desativar temporariamente um documento sem apagá-lo;
- reprocessar um documento mantendo histórico de versões;
- remover uma versão antiga sem remover a versão ativa.

## 9. Fluxos de erro

- permissão negada para ação administrativa;
- documento inexistente;
- tentativa de ativar versão inconsistente;
- falha ao remover chunks do `Chroma`;
- falha ao reprocessar uma nova versão;
- concorrência entre duas ações administrativas sobre o mesmo documento.

## 10. Regras de negócio

- somente documentos ativos podem entrar no fluxo de retrieval;
- desativar um documento deve retirá-lo do conjunto consultável;
- reprocessamento deve preservar trilha de auditoria;
- a versão ativa deve ser identificável de forma única;
- remoção ou desativação não pode deixar chunks órfãos sem rastreio.

## 11. Requisitos funcionais

- RF-01: listar documentos e versões da KB.
- RF-02: exibir status operacional do documento.
- RF-03: ativar e desativar documentos.
- RF-04: reprocessar um documento existente.
- RF-05: remover ou arquivar documento conforme a política adotada.
- RF-06: refletir mudanças no índice usado pelo RAG.

## 12. Requisitos não funcionais

- ações administrativas devem ser auditáveis;
- a UI deve refletir estados intermediários e finais;
- o sistema deve evitar inconsistência entre banco e `Chroma`;
- o gerenciamento deve suportar crescimento gradual da KB;
- erros administrativos devem ser devolvidos com mensagens seguras.

## 13. Contratos / interfaces

Exemplo de item listado:

```json
{
  "document_id": "doc_123",
  "title": "Tarifas 2026",
  "status": "active",
  "active_version": 3,
  "chunk_count": 42,
  "embedding_dimensions": 768,
  "updated_at": "2026-06-29T14:00:00Z"
}
```

Ação administrativa lógica:

```json
{
  "action": "deactivate",
  "document_id": "doc_123"
}
```

## 14. Modelo de dados necessário

- `KnowledgeDocument`;
- `KnowledgeDocumentVersion`;
- `KnowledgeIngestionJob`;
- `KnowledgeChunkMetadata`;
- marcação de versão ativa e status de disponibilidade.

## 15. Eventos e auditoria

- `kb.document_listed`;
- `kb.document_activated`;
- `kb.document_deactivated`;
- `kb.document_reprocessed`;
- `kb.document_deleted`;
- `kb.document_management_denied`.

## 16. Observabilidade

- documentos ativos e inativos;
- reprocessamentos executados;
- falhas de sincronização com o `Chroma`;
- tempo por ação administrativa;
- erros por tipo de operação.

## 17. Segurança e autorização

- exigir role apropriada para cada ação administrativa;
- impedir exposição de documentos inativos ao agent;
- registrar quem alterou cada documento;
- proteger operações destrutivas ou irreversíveis;
- não permitir que a UI seja fonte de verdade do status.

## 18. Critérios de aceite

- usuário autorizado consegue listar documentos da KB;
- ativar e desativar um documento altera sua disponibilidade para retrieval;
- reprocessar cria nova versão rastreável;
- remoção reflete no banco e no índice vetorial;
- ação negada não altera o estado do documento.

## 19. Casos de teste sugeridos

- listar documentos ativos e inativos;
- desativar documento ativo;
- ativar documento previamente inativo;
- reprocessar documento existente;
- negar ação para usuário sem permissão;
- falha ao sincronizar remoção com o `Chroma`.

## 20. Open questions

- a remoção será lógica, física ou suportará ambas?
- o reprocessamento troca automaticamente a versão ativa ou exige aprovação
  explícita?
- a tela mostrará prévia do conteúdo ou apenas metadados operacionais?
- o sistema permitirá gestão por tags, categorias ou coleções separadas?
