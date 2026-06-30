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

## Preparação do ambiente

- Antes de começar qualquer atividade de desenvolvimento, suba toda a
  infraestrutura local definida no `docker-compose.yml`.
- Considere como baseline de trabalho que `postgres`, `rabbitmq`, `chroma` e
  `litellm` devem estar disponíveis durante o desenvolvimento.
- Se a tarefa depender de backend, agents, identity ou fluxos integrados,
  valide primeiro que a infraestrutura está acessível.

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
- Quando não houver estado relevante ou ciclo de vida próprio, prefira funções
  a classes.
- Não introduza container de DI, service locator ou framework extra de injeção
  de dependência sem necessidade arquitetural clara.
- Não adicione parâmetros, branches, flags, hooks ou caminhos especiais no
  código de produto apenas para viabilizar testes.
- Para fluxos de decisão finitos e declarativos, prefira tabelas, dicts ou
  mapeamentos explícitos a cascatas extensas de `if`/`elif`.
- Quando testes precisarem isolar comportamento, faça isso do lado do teste com
  mocks, fakes, stubs ou doubles apropriados.

## Configuração e dependências de runtime

- Não defina valores padrão de banco, fila, credenciais, endpoints internos ou
  qualquer dependência de infraestrutura diretamente no código de runtime.
- Configurações de runtime devem vir de variáveis de ambiente, arquivos de
  configuração explícitos ou injeção de dependência.
- Quando uma configuração obrigatória estiver ausente, o sistema deve falhar de
  forma explícita e cedo, com erro claro, em vez de cair em fallback implícito.
- Não introduza fallback silencioso para SQLite, bancos locais, mocks ou
  serviços alternativos no código de produção.

## Persistência, models e migrations

- Toda mudança em model persistido, tabela, coluna, índice, constraint,
  relacionamento ou enum armazenado deve vir acompanhada da migration
  correspondente no projeto afetado.
- Cada projeto com persistência própria deve manter seu próprio conjunto de
  migrations.
- Não use `create_all`, DDL automático em runtime ou bootstrap estrutural da
  aplicação como substituto de migration.
- A ordem correta é: primeiro migrations estruturais; depois seed de dados
  dependentes da estrutura.
- Seed não substitui migration. Seed serve para dados iniciais, catálogos,
  permissões, roles e configurações dependentes de schema já existente.
- Quando houver seed inicial relevante para o domínio, ele deve acontecer
  somente depois que todas as tabelas, FKs, constraints e índices necessários
  já existirem.
- Ao alterar models, revise também se seeds, fixtures e contratos derivados
  precisam ser atualizados.
- Todo serviço executado pelo `docker-compose.yml` deve acessar o PostgreSQL
  pelo hostname do serviço `postgres`, nunca por `localhost`.
- Cada projeto que usa um schema PostgreSQL próprio deve manter também sua
  tabela `alembic_version` dentro desse schema, evitando conflito entre as
  migrations de `backend`, `agents` e `identity`.
- O comando `alembic upgrade head` deve funcionar tanto em um banco vazio
  quanto em um banco já atualizado, sem recriar tabelas ou repetir seeds.
- Containers com persistência devem executar `alembic upgrade head` com sucesso
  antes de iniciar a aplicação.
- Falha de migration deve impedir a inicialização da aplicação; não ignore,
  capture ou converta esse erro em inicialização parcial.
- `alembic stamp` não faz parte do startup normal. Use-o somente como operação
  explícita de baseline para um schema existente previamente verificado.

## Estrutura dos projetos Python

- Projetos Python do monorepo devem seguir o layout `nome_do_projeto/nome_do_projeto/`.
- O diretório externo representa o projeto, contendo arquivos como
  `pyproject.toml`, `README.md`, scripts e testes.
- O diretório interno representa o package Python importável e deve conter os
  módulos da aplicação, como `app`, `config`, `database`, `main`, `models`,
  `schemas` e `service`.
- Sempre que fizer sentido, mantenha os testes em `nome_do_projeto/tests/`.
- Exemplo:

```text
identity/
  pyproject.toml
  README.md
  identity/
    __init__.py
    app.py
    config.py
    database.py
    main.py
    models.py
    schemas.py
    service.py
  tests/
    test_identity_app.py
```

## Convenções Python

- Métodos e funções internas que não fazem parte da interface pública do módulo
  ou da classe devem começar com prefixo `_`.
- Helpers privados devem usar nomes como `_build_payload`, `_resolve_policy`,
  `_record_event`, etc.
- Só exponha sem `_` o que de fato fizer parte da API pública do módulo,
  componente ou classe.

## Dependências na borda HTTP

- Use mecanismos de injeção do framework, como `Depends`, somente na borda HTTP
  ou em adapters equivalentes.
- Não espalhe `Depends` ou abstrações do framework dentro de services,
  repositories, rules ou código core de domínio.
- O core deve permanecer em Python simples, recebendo dependências por
  argumento na função ou no construtor apenas quando isso fizer parte natural do
  fluxo de execução.
- Na borda HTTP, prefira resolver primeiro dependências técnicas como sessão,
  cliente ou contexto; em seguida, monte explicitamente o componente de domínio
  necessário e execute o fluxo.

## Diretrizes de testes

- Escreva testes quando eles adicionarem confiança real ao comportamento.
- Sempre que fizer sentido para a mudança, escreva primeiro o teste do cenário
  negativo, da negação ou da falha esperada antes do caminho feliz.
- Priorize testes para regras de negócio, contratos, autorização, fluxos
  críticos e regressões prováveis.
- Não crie testes apenas por cerimônia ou para cobrir código trivial.
- Mantenha testes objetivos, legíveis e focados em comportamento observável.
- Testes unitários não devem depender de banco real, fila real ou rede real.
- Em testes unitários, prefira fakes, mocks e repositórios em memória ao invés
  de SQLite, Postgres local ou infraestrutura do `docker-compose`.
- Em testes de rota ou adapter, prefira mockar ou stubbar o componente
  colaborador em vez de deformar o código de produção para facilitar o teste.
- Se a validação exigir banco real, trate isso explicitamente como teste de
  integração e não como teste unitário.
- Antes de commitar, execute os testes relevantes para a mudança realizada.

## Commit Rules

- **Rodar testes antes de todo commit**: Execute o comando de testes apropriado para a stack do projeto (ex: `npm test`, `uv run pytest`, `pnpm test`, `go test ./...`, etc.) para garantir que todos os testes passem antes de realizar um commit.
