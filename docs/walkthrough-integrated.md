# Walkthrough: integrated track

Keep EKS for orchestration; swap self-hosted backends for managed services. The agent code does not change. The diff between the two agent manifests is the whole migration, and it is four environment variables.

## 1. Inference: one line to Bedrock

```bash
source scripts/env.sh
./scripts/deploy-integrated.sh   # needs AGENTCORE_MEMORY_ID, see below
```

`MODEL_ID` flips from `qwen2-5-3b-neuron` to `nova-lite`. LiteLLM routes the name to Amazon Bedrock, authenticated by Pod Identity on the proxy's service account. The Inferentia fleet is no longer needed for this agent, and no agent code changed. This is what a model gateway buys you: the backend decision became reversible.

## 2. Observability: unchanged

Langfuse keeps tracing exactly as before; it never knew where inference happened. Same project, same trace tree, now with Bedrock latencies.

## 3. Memory: AgentCore Memory

Create a memory resource once (console or CLI), then:

```bash
export AGENTCORE_MEMORY_ID=<memory id>
```

`MEMORY_BACKEND=agentcore` switches the agent from Milvus recall to managed session memory: turns become events via `create_event`, recall reads the recent conversation. Storage, retention, and extraction strategies are now the service's problem.

## 4. Sandboxed tools: Code Interpreter + Browser

`AGENTCORE_TOOLS=1` gives the agent two new tools backed by managed sandboxes. "Total up my two orders" now runs real Python in an isolated session instead of trusting model arithmetic; live pages are read by a managed cloud browser. The agent pod itself gained no execution rights, no Chrome, and no new containers. Risky work left the cluster.

## 5. Multi-agent: unchanged

The A2A specialists redeploy against the new backends with two env values:

```bash
MODEL_ID=nova-lite AGENTCORE_TOOLS=1 ./scripts/deploy-self-managed.sh
```

Cards, discovery, routing: identical. The protocol layer does not care where models or tools live.

## 6. Evaluation: AgentCore Evaluations

The managed counterpart to the Langfuse judge. Three prerequisites, all provisioned by Terraform or one flag:

1. The agent runs with `AGENTCORE_OBSERVABILITY=1`, dual-exporting every span: Langfuse keeps its identical view, and a SigV4 OTLP exporter sends the same spans to the X-Ray endpoint, tagged with the three resource attributes the evaluations service looks for (`aws.service.type=gen_ai_agent`, the log group, the resource id).
2. CloudWatch Transaction Search is enabled. Be aware this is account-level: it routes X-Ray segments to CloudWatch Logs for the whole account and region.
3. Spans land in the account-wide `aws/spans` log group; allow 60 to 90 seconds of indexing after chatting.

Then, all CLI:

```bash
export AWS_REGION=...
./evaluation/agentcore/create-evaluator.sh    # once: the custom cs_accuracy evaluator
./evaluation/agentcore/run-evaluation.sh      # per conversation
```

Two built-in evaluators (Correctness, Helpfulness) ship with the service; `cs_accuracy` is the retail-specific judge you create, checking the agent called `lookup_order` rather than inventing order details, with Claude Sonnet 4.5 as the judge model.

### The finding that stayed with me

The integrated agent scored 1.0 on accuracy where the self-managed lab's conversations scored near zero. The agent was not smarter. Its traces were richer: tool-call spans tagged with `session.id` let the judge verify grounding directly, where the earlier traces could not prove it. Same judge methodology, richer traces, higher scores. Instrumentation quality is evaluation quality.

## What this track proves

Managed does not have to mean opaque or all-or-nothing. The logic stayed in code you own and debug; the heavy lifting (model fleets, sandbox isolation, memory retention, evaluation plumbing) became API calls. Each capability was swapped independently, and each swap is reversible by putting the old value back.
