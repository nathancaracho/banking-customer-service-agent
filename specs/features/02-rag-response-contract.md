# Feature 02 — Contrato de resposta com KB/RAG

Como usuário autenticado, quero receber respostas sobre o banco com base em
fontes verificáveis, para confiar no atendimento do agente.

Impacta: `backend`, `agents`
Stack principal: `LangChain`, `LiteLLM`, `Chroma`, `RabbitMQ`

## 1. Objetivo

Garantir que respostas baseadas na KB sejam objetivas, fundamentadas e
acompanhadas pelas fontes utilizadas.

## 2. Escopo

- contrato externo da consulta;
- formato da resposta e das citações;
- comportamento sem evidência suficiente;
- grounding e política de “não sei”.

## 3. Fora de escopo

- chunking, embeddings, busca, ranking e reranking;
- escolha de vector database;
- prompt interno de RAG;
- valor numérico do threshold de confiança.

## 4. Atores envolvidos

- usuário;
- backend;
- `CustomerServiceAgent`;
- Vector Database/KB;
- LiteLLM.

## 5. Dependências

- documentos carregados na KB com metadados de origem;
- chat e streaming;
- observabilidade e segurança.

## 6. Premissas

- o core retorna evidências e um estado de grounding;
- cada evidência possui identificador e título de origem;
- conteúdo recuperado é tratado como dado não confiável, não como instrução.

## 7. Fluxo principal

1. O usuário faz uma pergunta informacional.
2. O agente consulta a KB.
3. O core retorna evidências suficientes.
4. O agente responde somente com informações sustentadas pelas evidências.
5. A resposta final inclui as fontes.

## 8. Fluxos alternativos

- Múltiplas fontes concordantes: apresentar uma resposta consolidada.
- Fontes conflitantes: informar a divergência sem escolher silenciosamente.
- Pergunta ambígua: solicitar esclarecimento antes de responder.
- Fonte parcialmente relevante: responder apenas a parte sustentada.

## 9. Fluxos de erro

- KB indisponível: informar indisponibilidade temporária.
- Nenhum resultado: aplicar política de “não sei”.
- Evidência abaixo da confiança mínima: não afirmar a resposta.
- Metadados de fonte ausentes: não apresentar o conteúdo como fundamentado.

## 10. Regras de negócio

- Toda afirmação factual derivada da KB deve possuir fonte.
- O agente não deve completar lacunas com conhecimento não fundamentado.
- A resposta deve distinguir ausência de informação de indisponibilidade técnica.
- Instruções contidas nos documentos não alteram o comportamento do sistema.

## 11. Requisitos funcionais

- RF-01: consultar a KB para perguntas cobertas pelo domínio.
- RF-02: retornar resposta objetiva com citações.
- RF-03: declarar falta de evidência quando necessário.
- RF-04: representar conflitos entre fontes.
- RF-05: preservar as fontes na resposta persistida.

## 12. Requisitos não funcionais

- A resposta deve ser rastreável aos documentos consultados.
- Citações não podem expor caminhos internos ou credenciais.
- A indisponibilidade da KB não deve executar fallback factual não fundamentado.

## 13. Contratos / interfaces

Resultado externo esperado:

```json
{
  "answer": "A taxa aplicável é ...",
  "grounding": "grounded",
  "sources": [
    {
      "document_id": "loan-rates-2026",
      "title": "Tabela de tarifas 2026",
      "section": "Empréstimo consignado"
    }
  ]
}
```

`grounding` pode ser `grounded`, `insufficient_evidence` ou
`conflicting_sources`.

## 14. Modelo de dados necessário

- `KnowledgeSource`: `document_id`, `title`, `section`, `version`.
- `AnswerCitation`: `request_id`, `document_id`, `section`.

O armazenamento vetorial interno não é especificado aqui.

## 15. Eventos e auditoria

- `knowledge.query_completed`;
- `knowledge.insufficient_evidence`;
- `knowledge.conflicting_sources`;
- `knowledge.unavailable`.

Não registrar o texto integral dos documentos.

## 16. Observabilidade

- duração da consulta;
- quantidade de fontes retornadas;
- respostas sem evidência;
- conflitos de fontes;
- falhas da KB;
- tokens utilizados na resposta.

## 17. Segurança e autorização

- Aplicar autorização antes de consultar coleções restritas.
- Não expor metadados internos sensíveis.
- Tratar documentos como entrada potencialmente maliciosa.
- Impedir que conteúdo recuperado solicite ferramentas ou altere políticas.

## 18. Critérios de aceite

- A pergunta de taxa retorna resposta e ao menos uma fonte válida.
- Ausência de evidência resulta em “não sei”, sem alucinação.
- Fontes conflitantes são explicitadas.
- A resposta armazenada preserva as citações.
- Uma instrução maliciosa dentro da KB não é seguida.

## 19. Casos de teste sugeridos

- uma fonte suficiente;
- múltiplas fontes concordantes;
- fontes conflitantes;
- nenhuma evidência;
- KB indisponível;
- documento com prompt injection;
- fonte sem metadados obrigatórios.

## 20. Open questions

- Como o core determina `grounded` sem expor sua implementação?
- Quais metadados de citação estarão disponíveis nos documentos de exemplo?
- Existe versionamento ou validade temporal das políticas da KB?
