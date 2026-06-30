# AGENTS.md

## Leitura obrigatória

Antes de analisar, implementar ou revisar qualquer alteração neste repositório,
leia nesta ordem:

1. `AGENTS.md`
2. `specs/architecture.md`
3. `specs/tech-stack.md`
4. `specs/features/README.md`
5. a feature spec relevante em `specs/features/*.md`
6. os ADRs relevantes em `specs/adrs/*.md`

## Fonte de verdade

Os caminhos canônicos de documentação deste projeto estão em `specs/`.

Use como referência principal:

- `specs/architecture.md` para responsabilidades, limites entre projetos,
  fluxos, filas e contratos de alto nível;
- `specs/tech-stack.md` para stack adotada, bibliotecas por projeto e rationale
  técnico;
- `specs/features/*.md` para comportamento esperado, dependências entre
  features, projetos impactados e contratos observáveis;
- `specs/adrs/*.md` para decisões arquiteturais e seus trade-offs.

Se encontrar documentação duplicada fora de `specs/`, trate `specs/` como fonte
de verdade.

## Como usar as specs

- Antes de codar, identifique qual feature ou ADR a tarefa toca.
- Preserve os limites entre `frontend`, `backend`, `agents` e `identity`.
- Respeite o ownership definido na arquitetura. Exemplo: memória do chat no
  `backend`, checkpoint técnico em `agents`, autorização no `identity`.
- Ao propor nova biblioteca, serviço, fila, banco ou padrão relevante, verifique
  primeiro `specs/tech-stack.md` e os ADRs existentes.
- Não contradiga uma ADR aceita sem atualizar a própria ADR ou criar uma nova.

## Quando atualizar a documentação

Atualize a documentação correspondente sempre que a mudança alterar:

- responsabilidades entre projetos do monorepo;
- fluxo entre backend, agents, identity, filas ou MCP;
- stack técnica ou bibliotecas principais;
- contratos externos, payloads, eventos ou políticas de autorização;
- comportamento funcional descrito em uma feature spec.

Em geral:

- mudança de comportamento: atualize a feature em `specs/features/`;
- mudança de stack: atualize `specs/tech-stack.md`;
- mudança arquitetural ou de fluxo: atualize `specs/architecture.md`;
- mudança de decisão relevante: atualize ou crie uma ADR em `specs/adrs/`.

## Diretrizes de código

- Evite comentários desnecessários.
- Comentários devem explicar o **porquê**, não o **o quê**.
- Só adicione comentários quando forem estritamente necessários para registrar
  contexto, trade-off, restrição ou decisão não óbvia.
- Prefira código legível, pequeno e explícito em vez de comentários
  explicativos.
- Prefira estilo predominantemente funcional e composição simples.
- Evite abstrações prematuras, camadas artificiais e orientação a objetos sem
  necessidade concreta.

## Diretrizes de testes

- Escreva testes quando eles adicionarem confiança real ao comportamento.
- Sempre que fizer sentido para a mudança, escreva primeiro o teste do cenário
  negativo, da negação ou da falha esperada antes do caminho feliz.
- Priorize testes para regras de negócio, contratos, autorização, fluxos
  críticos e regressões prováveis.
- Não crie testes apenas por cerimônia ou para cobrir código trivial.
- Mantenha testes objetivos, legíveis e focados em comportamento observável.
- Antes de commitar, execute os testes relevantes para a mudança realizada.

## Commit Rules

- **Rodar testes antes de todo commit**: Execute o comando de testes apropriado para a stack do projeto (ex: `npm test`, `uv run pytest`, `pnpm test`, `go test ./...`, etc.) para garantir que todos os testes passem antes de realizar um commit.
