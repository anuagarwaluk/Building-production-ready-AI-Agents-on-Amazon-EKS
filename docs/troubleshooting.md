# Troubleshooting

Failure modes you are likely to meet with this stack, ordered by where they bite.

## Model plane

**Agent returns 500 and logs an OpenAI connection error.**
The agent only ever talks to LiteLLM, so debug the plane, not the backend. `kubectl -n litellm logs deploy/litellm` shows which route failed. Test the plane directly with a curl to `/v1/chat/completions`; if that works, the problem is the agent's `LITELLM_BASE_URL` or `MODEL_ID` spelling.

**`nova-lite` route fails with AccessDenied.**
Bedrock model access is per-region and per-model: enable Nova Lite (and the judge model) in the Bedrock console for your region. Then confirm the litellm ServiceAccount's Pod Identity association exists: `aws eks list-pod-identity-associations --cluster-name <name>`.

**`qwen2-5-3b-neuron` route times out.**
Check the chain in order: vLLM pod Ready? (`kubectl -n vllm get pods`; first start takes minutes for node provisioning, model download, and Neuron compilation). Service reachable? (`curl` from a debug pod to `qwen2-5-3b-neuron.vllm:8000/v1/models`). Only then blame LiteLLM.

**Pods stuck Pending on the Inferentia pool.**
`kubectl describe pod` distinguishes the three usual causes: no inf2 capacity in the AZs (try another region or family), the NodePool taint without a matching toleration, or an account quota of zero for inf2 instances.

## Tools and data

**Agent answers order questions but invents details.**
Almost always means the tool did not load, and the model free-styled. Startup logs list loaded tools. With `ORDERS_TOOL_MODE=mcp`, verify the MCP URL ends in `/mcp` and is reachable across namespaces. The system prompt tells the agent to refuse rather than guess, but a missing tool plus a small model still needs watching; this is exactly what the accuracy evaluator catches.

**`search_products` returns nothing after seeding.**
Embedding model mismatch. The seeder and the agent must use the same `EMBED_MODEL`; vectors from different models share no geometry. Also confirm you seeded through the same port-forward you think you did.

**Memory recalls nothing (Milvus backend).**
Recall filters on `session_id`. The UI generates one per conversation; a fresh browser session is a fresh memory. Confirm turns are inserting: the collection row count should grow after each exchange.

**AgentCore Memory errors NotFound.**
`AGENTCORE_MEMORY_ID` must be an existing memory resource in the same region the pod's `AWS_REGION` points at. Region mismatch is the usual cause; AgentCore services are region-dependent.

## A2A

**Orchestrator finds no specialists.**
Discovery starts at the card: `curl http://order-agent.agents:9000/.well-known/agent-card.json` from a debug pod. If the card's advertised URL says `localhost`, the specialist's `A2A_URL` env is missing, and callers will discover an agent they cannot call back.

## Evaluation

**`run-evaluation.sh` collects 0 spans.**
In order: wait 60 to 90 seconds after chatting (indexing lag); confirm the agent runs with `AGENTCORE_OBSERVABILITY=1`; confirm Transaction Search is enabled for the account; and look in `aws/spans` (account-wide), not the per-agent log group. The exporter also needs its explicit X-Ray endpoint; without it, spans silently go to localhost:4318.

**Accuracy scores near zero on conversations that look fine.**
The judge can only verify grounding from tool-call spans. Traces without them cannot prove the agent used `lookup_order`, so grounding fails even when the answer was right. Fix the instrumentation, not the agent.

**Langfuse shows the trace twice or not at all after enabling dual export.**
Both exporters must hang off ONE global TracerProvider, and Langfuse v4 wires its own processor when you pass `tracer_provider=` to the client. Creating a second provider, or calling `get_client()` instead of using the returned client, causes exactly these symptoms.

## Cluster

**`exec format error` in pod logs.**
Image built for arm64 on an Apple Silicon laptop. Every build script pins `--platform linux/amd64` for this reason.

**Terraform destroy hangs on the VPC.**
Something still holds ENIs, usually a load balancer or the Inferentia node. Delete workloads and NodePools first; `scripts/cleanup.sh` does this in the right order.
