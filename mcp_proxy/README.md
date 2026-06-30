# MCP Proxy

Servidor FastMCP que expõe as operações bancárias utilizadas pelo
`CustomerServiceAgent` e traduz as tools para chamadas HTTP à `banking_api`.

O Identity não faz parte deste serviço. A autorização ocorre no middleware do
Agent antes da execução da tool.

O servidor usa o transporte MCP `streamable-http`. HTTPS deve ser terminado no
proxy de entrada ou túnel usado no deploy.
