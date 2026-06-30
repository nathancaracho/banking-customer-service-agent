# Feature Spec: Resposta com Base em KB / RAG (Comportamento Externo)

## 1. Objetivo

Especificar o contrato de entrada e saída das respostas baseadas na base de conhecimento (KB/RAG), incluindo formato, citação de fontes, grounding, política de "não sei" e critérios de confiança. O pipeline interno de retrieval não é detalhado aqui.

## 2. Escopo

- Contrato de pergunta e resposta via RAG
- Formato da resposta com citações
- Grounding das respostas na KB
- Tratamento de ausência de fonte
- Política de "não sei" e recusa educada
- Critérios de confiança mínimos

## 3. Fora de Escopo

- Pipeline interno de chunking, embedding e ranking
- Estratégia interna de retrieval
- Implementação do motor de guardrails
- Indexação e atualização da base de conhecimento
- Operações bancárias (ver specs 03, 05)

## 4. Atores Envolvidos

- **Usuário**: cliente ou funcionário que faz perguntas ao agente
- **Agente (core)**: black box que orquestra retrieval e geração
- **Vector DB**: ChromaDB com documentos e embeddings da KB
- **LiteLLM**: gateway para o modelo de linguagem
- **Backend**: gerencia sessão, memória e filas

## 5. Dependências

- Vector DB (ChromaDB) com KB indexada
- LiteLLM (modelo de linguagem)
- Agent (core)
- Request/Reply queues

## 6. Premissas

- A base de conhecimento contém documentos oficiais do banco (taxas, regras, procedimentos)
- O Vector DB já está populado com documentos chunked e embeddados
- O agente é responsável por selecionar documentos relevantes (não detalhado aqui)
- Respostas sem grounding adequado seguem a política de "não sei"

## 7. Fluxo Principal

1. Usuário envia pergunta via chat (ex: "Qual a taxa do empréstimo consignado para aposentados?")
2. Backend publica requisição na `request_queue` com a mensagem e memória
3. Agente recebe a requisição e identifica a intenção de consulta à KB
4. Agente consulta Vector DB com a pergunta
5. Vector DB retorna documentos relevantes com pontuação de similaridade
6. Agente gera resposta com base nos documentos, citando fontes
7. Agente publica chunks da resposta na `reply_queue`
8. Backend entrega chunks via SSE ao frontend

## 8. Fluxos Alternativos

### 8.1. Nenhum Documento Relevante Encontrado

- Se nenhum documento atingir o limiar de confiança:
  - Agente publica resposta: "Não encontrei essa informação na base de conhecimento do banco."
  - Agente sugere reformular a pergunta ou falar com um atendente humano

### 8.2. Confiança Baixa

- Se a pontuação máxima estiver entre o limiar mínimo e o limiar ideal:
  - Agente gera resposta com ressalva: "De acordo com documentos disponíveis, [resposta]. Recomendo confirmar com seu gerente."
  - Agente inclui a citação mesmo com baixa confiança

### 8.3. Pergunta Ambígua

- Se a pergunta puder ter múltiplas interpretações:
  - Agente publica `chunk` pedindo esclarecimento
  - Exemplo: "Você quer saber a taxa para aposentados do INSS ou do regime próprio?"

## 9. Fluxos de Erro

### 9.1. Vector DB Indisponível

- Agente detecta falha de conexão com ChromaDB
- Publica `event: failed` com `{ error: "knowledge_base_unavailable", message: "A base de conhecimento está temporariamente indisponível." }`
- Sugere tentar novamente mais tarde

### 9.2. Documentos Irrelevantes Retornados

- Agente avalia que documentos retornados não respondem à pergunta
- Aplica política de "não sei" (seção 10.2)

### 9.3. Alucinação Detectada

- Se o motor de guardrails detectar resposta não grounded:
  - Agente descarta resposta e publica "Não posso responder com segurança a essa pergunta."
  - Registra evento de auditoria de alucinação

## 10. Regras de Negócio

### 10.1. Critérios de Confiança

| Nível | Threshold | Comportamento |
|-------|-----------|---------------|
| Alto | >= 0.85 | Resposta direta com citação |
| Médio | 0.70 a 0.84 | Resposta com ressalva |
| Baixo | 0.50 a 0.69 | "Não tenho certeza, mas..." |
| Insuficiente | < 0.50 | "Não sei" |

### 10.2. Política de "Não Sei"

- O agente deve explicitamente dizer "não sei" em vez de inventar
- Frase padrão: "Não encontrei essa informação na base de conhecimento disponível."
- Não deve sugerir informações financeiras incorretas
- Deve oferecer alternativa: "Posso encaminhar sua dúvida para um atendente humano?"

### 10.3. Citação de Fontes

- Toda resposta RAG deve incluir ao menos uma citação
- Formato da citação: `[Doc: Nome do Documento, Versão X.X]`
- Citações são incluídas como metadado no chunk, não no texto visível
- O frontend pode renderizar citações como tooltips ou notas

## 11. Requisitos Funcionais

| ID | Descrição |
|----|-----------|
| RF01 | Responder perguntas com base na KB |
| RF02 | Incluir citação da fonte na resposta |
| RF03 | Informar "não sei" quando não houver documento relevante |
| RF04 | Informar dúvida quando confiança for baixa |
| RF05 | Pedir esclarecimento em perguntas ambíguas |
| RF06 | Sugerir encaminhamento para humano quando necessário |

## 12. Requisitos Não Funcionais

| ID | Descrição |
|----|-----------|
| RNF01 | Resposta RAG em menos de 10s (primeiro chunk) |
| RNF02 | Tamanho máximo da resposta: 4096 caracteres |
| RNF03 | Limiar de confiança mínimo default: 0.50 |
| RNF04 | Ao menos 1 fonte citada por resposta RAG |
| RNF05 | Nenhuma resposta fabricada sem grounding |

## 13. Contratos / Interfaces

### Entrada do RAG pelo agente (interface interna)

```json
{
  "query": "Qual a taxa do empréstimo consignado para aposentados?",
  "chat_id": "uuid",
  "auth_context": "token"
}
```

### Saída esperada do Vector DB (interface interna)

```json
{
  "results": [
    {
      "document_id": "uuid",
      "content": "Taxa de empréstimo consignado para aposentados: 1.8% ao mês...",
      "source": "Manual de Produtos - v2.3",
      "score": 0.92
    }
  ]
}
```

### Resposta final (chunk no SSE)

```json
{
  "type": "chunk",
  "sequence": 1,
  "payload": {
    "content": "A taxa do empréstimo consignado para aposentados é de 1,8% ao mês.",
    "citations": [
      { "source": "Manual de Produtos - v2.3", "document_id": "uuid" }
    ],
    "confidence": 0.92
  }
}
```

### Ausência de fonte

```json
{
  "type": "chunk",
  "sequence": 1,
  "payload": {
    "content": "Não encontrei essa informação na base de conhecimento disponível. Tente reformular a pergunta ou falar com um atendente humano.",
    "citations": [],
    "confidence": 0.0
  }
}
```

## 14. Modelo de Dados Necessário

### Vector DB (ChromaDB) - já existente

Coleção: `knowledge_base`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | string | UUID do documento |
| content | string | Texto do chunk |
| metadata.source | string | Nome/versão do documento fonte |
| metadata.category | string | Categoria (produtos, taxas, procedimentos) |
| metadata.updated_at | string | Data da última atualização |
| embedding | float[] | Vetor de embedding |

## 15. Eventos e Auditoria

| Evento | Trigger | Informação |
|--------|---------|------------|
| rag.query | Consulta à KB executada | chat_id, request_id, query |
| rag.response | Resposta gerada | chat_id, request_id, confidence, sources |
| rag.no_results | Nenhum documento encontrado | chat_id, request_id, query |
| rag.low_confidence | Confiança abaixo do limiar | chat_id, request_id, confidence, threshold |
| rag.hallucination | Possível alucinação detectada | chat_id, request_id, response_preview |

## 16. Observabilidade

Métricas:
- `rag.query_total`: total de consultas RAG
- `rag.query_duration_seconds`: latência das consultas
- `rag.confidence_distribution`: distribuição dos scores de confiança
- `rag.no_result_ratio`: proporção de consultas sem resultado
- `rag.hallucination_rate`: taxa de possíveis alucinações

## 17. Segurança e Autorização

- A KB é pública para todos os perfis autenticados (leitura)
- Consultas RAG são registradas para auditoria
- O agente não deve expor documentos internos não públicos
- Metadados de documentos não devem conter informações sensíveis

## 18. Critérios de Aceite

1. Pergunta com documento relevante retorna resposta com citação
2. Pergunta sem documento relevante retorna "não sei"
3. Confiança baixa gera resposta com ressalva
4. Pergunta ambígua gera pedido de esclarecimento
5. Resposta nunca inventa informação sem grounding
6. Citações são incluídas como metadados em todos os chunks RAG

## 19. Casos de Teste Sugeridos

| Caso | Cenário | Resultado Esperado |
|------|---------|--------------------|
| CT01 | Pergunta com documento exato | Resposta com citação, confidence >= 0.85 |
| CT02 | Pergunta sem documento relevante | "Não sei", confidence < 0.50 |
| CT03 | Pergunta com confiança baixa | Resposta com ressalva |
| CT04 | Pergunta ambígua | Pedido de esclarecimento |
| CT05 | Vector DB indisponível | Erro amigável |
| CT06 | Alucinação detectada internamente | Evento de auditoria, fallback |

## 20. Open Questions

1. A KB será carregada estaticamente ou atualizada dinamicamente?
2. Deve haver versões diferentes da KB para perfis diferentes (customer vs manager)?
3. Como documentos com informação conflitante são tratados?
4. Quem é responsável pela curadoria e atualização dos documentos?
