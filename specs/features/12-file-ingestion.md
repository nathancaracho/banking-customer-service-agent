# Feature 12 — Ingestion e gestão da base de conhecimento

Como responsável pela base de conhecimento, quero enviar arquivos para a
plataforma, acompanhar seu processamento e gerenciar sua disponibilidade, para
alimentar o RAG do agente com conteúdo atualizado e confiável.

Domínio principal: `knowledge_base`
Projeto principal: `backend`
Impacta: `frontend`, `backend`, `identity`
Stack principal: `React`, `FastAPI`, `Chroma`, `LiteLLM`, `PostgreSQL`

## 1. Objetivo

Permitir que usuários autorizados façam upload, listem, ativem, desativem,
reprocessem e removam documentos da KB por uma tela dedicada, com
processamento no backend, chunking configurado em `700` com `overlap` de `200`
e geração de embeddings com dimensionalidade inicial fixa em `768`.

## 2. Escopo

- tela de upload de arquivos da KB;
- listagem de documentos já ingeridos;
- exibição de status, versão e metadados principais;
- endpoint backend para receber arquivos e criar a ingestão;
- extração de texto do arquivo recebido;
- chunking com tamanho `700` e overlap `200`;
- geração de embeddings;
- persistência de metadados no banco e chunks no `Chroma`;
- status de processamento visível para o usuário;
- ativação, desativação, reprocessamento e remoção lógica do documento.

## 3. Fora de escopo

- OCR avançado para arquivos escaneados;
- deduplicação semântica sofisticada;
- versionamento editorial completo;
- edição inline do conteúdo do documento;
- workflow editorial complexo com múltiplos aprovadores;
- re-ranking avançado no momento da recuperação.

## 4. Atores envolvidos

- usuário administrativo autorizado;
- frontend;
- backend;
- `Identity`;
- `Chroma`;
- provider de embeddings configurado no projeto;
- `CustomerServiceAgent` como consumidor indireto da KB.

## 5. Dependências

- Feature 06 - RBAC;
- Feature 07 - Auditoria;
- Feature 08 - Observabilidade;
- Feature 10 - Segurança e guardrails;
- Feature 11 - Identity service.

## 6. Premissas

- a ingestão é responsabilidade do backend, não do agent;
- o backend é responsável por parsing, chunking e indexação;
- somente usuários autorizados podem ingerir arquivos;
- o chunking usa tamanho `700` com overlap `200` na configuração inicial;
- a dimensão inicial da coleção é fixa em `768`.
- o agent consome apenas documentos ativos.

## 7. Fluxo principal

1. O usuário acessa a tela de file ingestion.
2. O frontend envia o arquivo e os metadados ao backend.
3. O backend valida autenticação e permissão no `Identity`.
4. O backend registra a solicitação de ingestão.
5. O backend extrai o texto do arquivo.
6. O backend divide o conteúdo em chunks de `700` com overlap `200`.
7. O backend gera embeddings para cada chunk.
8. O backend grava os metadados da ingestão no banco.
9. O backend indexa os chunks e embeddings no `Chroma`.
10. O backend atualiza o status para concluído e devolve o resultado ao
    frontend.

## 8. Fluxos alternativos

- arquivo pequeno gera poucos chunks;
- arquivo sem título explícito usa o nome original como referência inicial;
- ingestão de nova versão do mesmo documento cria uma nova versão lógica;
- usuário salva o documento como inativo, sem expô-lo imediatamente ao RAG;
- usuário lista documentos já ingeridos;
- usuário ativa ou desativa um documento existente;
- usuário reprocessa um documento mantendo histórico de versões;
- usuário remove logicamente um documento da base.

## 9. Fluxos de erro

- formato não suportado;
- arquivo vazio ou sem texto extraível;
- permissão negada pelo `Identity`;
- falha na geração de embeddings;
- falha ao indexar no `Chroma`;
- inconsistência entre metadados persistidos e chunks indexados;
- documento inexistente para ação administrativa;
- falha ao reprocessar ou desativar um documento;
- concorrência entre duas ações administrativas sobre o mesmo documento.

## 10. Regras de negócio

- o backend executa toda a pipeline de ingestão;
- chunks devem ser gerados com tamanho `700` e overlap `200` na configuração
  inicial;
- a dimensão do embedding deve permanecer consistente dentro da coleção;
- documentos inativos não podem ser recuperados pelo agente;
- a ingestão deve registrar origem, autor da ação e status final;
- somente documentos ativos podem entrar no fluxo de retrieval;
- reprocessamento deve preservar trilha de auditoria e versionamento.

## 11. Requisitos funcionais

- RF-01: permitir upload de arquivos por usuários autorizados.
- RF-02: validar o acesso antes do processamento.
- RF-03: extrair texto e gerar chunks com `700/200`.
- RF-04: gerar embeddings com dimensionalidade `768`.
- RF-05: persistir metadados da ingestão.
- RF-06: indexar os chunks no `Chroma`.
- RF-07: retornar status de sucesso ou falha ao frontend.
- RF-08: listar documentos e versões da KB.
- RF-09: ativar e desativar documentos.
- RF-10: reprocessar documento existente.
- RF-11: remover ou arquivar documento conforme a política adotada.

## 12. Requisitos não funcionais

- o processamento deve ser rastreável por `request_id` ou `ingestion_id`;
- falhas de indexação não podem deixar status ambíguo sem rastreio;
- a coleção deve usar uma única dimensionalidade por versão ativa;
- a ingestão deve falhar de forma segura quando o arquivo for inválido;
- o pipeline deve suportar reprocessamento futuro do mesmo documento;
- o sistema deve evitar inconsistência entre banco e `Chroma` em ações
  administrativas.

## 13. Contratos / interfaces

Requisição lógica:

```json
{
  "file_name": "tarifas-2026.pdf",
  "content_type": "application/pdf",
  "source": "manual_upload",
  "active": true
}
```

Resposta lógica:

```json
{
  "ingestion_id": "ing_123",
  "document_id": "doc_123",
  "status": "completed",
  "chunk_size": 700,
  "chunk_overlap": 200,
  "embedding_dimensions": 768,
  "chunk_count": 42
}
```

Item de listagem:

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
- referência da coleção e da versão indexada no `Chroma`;
- marcação de versão ativa e status de disponibilidade.

## 15. Eventos e auditoria

- `kb.ingestion_requested`;
- `kb.ingestion_started`;
- `kb.ingestion_completed`;
- `kb.ingestion_failed`;
- `kb.document_activated`;
- `kb.document_activation_denied`;
- `kb.document_deactivated`;
- `kb.document_reprocessed`;
- `kb.document_deleted`.

## 16. Observabilidade

- quantidade de arquivos ingeridos;
- tempo de parsing;
- tempo de chunking;
- tempo de geração de embeddings;
- tempo de indexação no `Chroma`;
- chunks por documento;
- falhas por tipo de arquivo e por etapa;
- documentos ativos e inativos;
- falhas de sincronização em ações administrativas.

## 17. Segurança e autorização

- validar autenticação e permissão antes do upload;
- exigir role apropriada para cada ação administrativa;
- limitar tipos e tamanho de arquivo;
- não expor conteúdo bruto em logs comuns;
- registrar o ator da ingestão na auditoria;
- impedir que documentos inativos entrem no fluxo de retrieval;
- não permitir que a UI seja fonte de verdade do status.

## 18. Critérios de aceite

- usuário autorizado consegue enviar um arquivo e concluir a ingestão;
- o backend gera chunks com `700` e overlap `200`;
- a ingestão grava metadados e indexa o conteúdo no `Chroma`;
- falha em permissão impede o processamento;
- arquivos inativos não ficam disponíveis para uso pelo agente;
- ativar, desativar e reprocessar documento altera corretamente seu estado.

## 19. Casos de teste sugeridos

- upload autorizado de PDF válido;
- upload negado por falta de permissão;
- arquivo sem texto útil;
- falha na geração de embeddings;
- falha na indexação no `Chroma`;
- validação do número de chunks gerado pelo splitter configurado;
- desativar documento ativo;
- reprocessar documento existente;
- negar ação administrativa para usuário sem permissão.

## 20. Open questions

- quais formatos entram na primeira versão: `pdf`, `txt`, `md`, `docx`?
- a ingestão será síncrona na request inicial ou assíncrona com polling?
- a coleção do `Chroma` será única por ambiente ou separada por domínio de KB?
- quando o modelo de embedding mudar, a estratégia será recriar a coleção ou
  manter múltiplas versões ativas?
- a remoção será lógica, física ou suportará ambas?
