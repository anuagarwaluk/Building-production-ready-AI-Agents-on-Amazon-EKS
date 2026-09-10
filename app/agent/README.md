# Customer Agent

The Strands agent behind AnyCompany Shop's customer service chat. One codebase, four roles, two infrastructure tracks.

## Four entrypoints, one image

| Entrypoint | Role | Port |
|---|---|---|
| `customer-agent` | Single agent serving `/chat` | 8000 |
| `orchestrator-agent` | Multi-agent front door, routes over A2A | 8000 |
| `order-agent` | Order/inventory/returns specialist (A2A) | 9000 |
| `product-agent` | Product/RAG/sandbox specialist (A2A) | 9000 |

## Capabilities are configuration

The agent gains one capability per workshop lab, and each is an environment switch here:

| Env | Effect |
|---|---|
| `MODEL_ID` | `qwen2-5-3b-neuron` (self-hosted vLLM) or `nova-lite` (Bedrock). LiteLLM absorbs the difference. |
| `LITELLM_BASE_URL` | The one endpoint the agent ever calls for inference |
| `ORDERS_TOOL_MODE` | `local` (lab 1 hardcoded data) or `mcp` (shop MCP server) |
| `MILVUS_URI` | Enables product RAG; also used by Milvus memory |
| `MEMORY_BACKEND` | `none`, `milvus` (semantic recall), or `agentcore` (managed) |
| `AGENTCORE_MEMORY_ID` | Memory resource id for the agentcore backend |
| `NEO4J_URI` | Enables the knowledge graph tool |
| `AGENTCORE_TOOLS` | `1` adds Code Interpreter and Browser sandbox tools |
| `LANGFUSE_PUBLIC_KEY` / `SECRET_KEY` / `BASE_URL` | Tracing to Langfuse |
| `AGENTCORE_OBSERVABILITY` | `1` dual-exports spans to AgentCore Observability for evaluations |

## Run locally

```bash
cd app/agent
uv sync
LITELLM_BASE_URL=http://localhost:4000 MODEL_ID=nova-lite uv run customer-agent
curl -X POST localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"message": "Where is my order ORD-12345?"}'
```

## Test

```bash
uv run --extra test pytest
```
