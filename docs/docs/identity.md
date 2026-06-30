# Identity

Serviço de autenticação, autorização e gestão de usuários.

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/v1/auth/register` | Registrar usuário |
| `POST` | `/v1/auth/login` | Login |
| `POST` | `/v1/authorization/check` | Verificar autorização |

## Modelo de Dados

### Usuário

```python
class User(Base):
    id: str           # UUID
    email: str
    hashed_password: str
    roles: list[str]  # ex: ["customer"], ["manager"], ["admin"]
    created_at: datetime
```

### Role

```python
class Role(Base):
    id: str
    name: str         # ex: "customer", "manager", "admin"
    permissions: list[str]
```

## Autorização

### Requisito

```python
class AuthorizationRequest(BaseModel):
    subject: Subject           # { user_id, roles }
    action: str                # ex: "balance.read", "pix.transfer"
    resource: AuthorizationResource  # { type, owner_id }
    parameters: dict | None
    context: AuthorizationContext    # { request_id, chat_id, tool_name }
```

### Resposta

```python
class AuthorizationResponse(BaseModel):
    decision: Literal["allow", "deny"]
    reason: str
    policy_version: str
    subject: Subject
```

### Fluxo

1. Agent middleware intercepta tool call
2. Constrói `AuthorizationRequest` com contexto
3. Envia para Identity via HTTP
4. Identity valida:
   - Usuário autenticado
   - Role possui permissão para a ação
   - Recurso pertence ao usuário (ou é público)
5. Retorna `allow` ou `deny`
6. Se `deny`, tool não é executada

### Recursos Protegidos

| Tool | Ação | Recurso |
|---|---|---|
| `get_balance` | `balance.read` | `customer_account` |
| `get_card_limit` | `card_limit.read` | `credit_card` |
| `execute_limit_update` | `card_limit.read` | `credit_card` |
| `execute_limit_update` | `card_limit.update` | `credit_card` |
| `execute_pix` | `balance.read` | `customer_account` |
| `execute_pix` | `pix.transfer` | `bank_account` |

## Políticas

Políticas definem quem pode fazer o quê:

```python
class Policy(Base):
    id: str
    name: str
    effect: Literal["allow", "deny"]
    actions: list[str]       # ex: ["balance.read"]
    resource_types: list[str]  # ex: ["customer_account"]
    roles: list[str]         # ex: ["customer"]
    conditions: dict         # critérios adicionais
```

### Exemplo

```json
{
    "effect": "allow",
    "actions": ["balance.read"],
    "resource_types": ["customer_account"],
    "roles": ["customer"],
    "conditions": {
        "owner_match": true
    }
}
```

Isso significa: customers podem ler saldo de contas que possuem.

## Auditoria

Todas as decisões de autorização são registradas:

```python
class AuthorizationAudit(Base):
    id: str
    subject_id: str
    action: str
    resource_type: str
    decision: str
    reason: str
    policy_version: str
    request_id: str
    chat_id: str
    created_at: datetime
```

## Observabilidade

- `identity.authorization.total` — total de verificações
- `identity.authorization.allow` / `deny` — decisões
- `identity.authorization.duration_ms` — latência

## Configuração

| Variável | Default | Descrição |
|---|---|---|
| `IDENTITY_DATABASE_URL` | — | PostgreSQL connection string |
| `IDENTITY_DATABASE_SCHEMA` | `identity` | Schema PostgreSQL |
