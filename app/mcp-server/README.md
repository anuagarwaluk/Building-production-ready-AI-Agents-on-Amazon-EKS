# Shop MCP Server

Business tools for AnyCompany Shop, served over the Model Context Protocol so any agent (or any MCP client) can use them without owning them.

| Tool | What it does |
|---|---|
| `lookup_order` | Order status, items, totals, tracking |
| `check_inventory` | Stock levels and restock ETA |
| `process_return` | Starts a return under the 30 day policy |

The point of the lab this comes from: tools moved out of the agent's codebase and behind a protocol. The agent's `ORDERS_TOOL_MODE=mcp` switch is the only change on the consumer side.

## Run locally

```bash
uv run shop-mcp --transport streamable-http   # :8080/mcp
```
