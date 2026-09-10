# AI Agents on Amazon EKS

I built a customer service agent for a fictional online store, deployed it on Amazon EKS, then rebuilt its infrastructure twice: once fully self-managed on open source, once integrating AWS managed services. The agent code is the same in both. The migration between them is a handful of environment variables, because a model gateway and two protocols (MCP, A2A) absorb every backend decision.

This is my hands-on build from the AWS **AI Agents on Amazon EKS** workshop, restructured as a deployable reference with my own code, deployment scripts, documentation, and troubleshooting notes.

![Self-managed architecture](docs/images/architecture-self-managed.png)

## The two tracks

| Capability | Self-managed track | Integrated track |
|---|---|---|
| Model inference | Qwen2.5-3B on vLLM, AWS Inferentia | Amazon Bedrock (Nova Lite) |
| Agent orchestration | Strands Agents SDK on EKS | Strands Agents SDK on EKS (unchanged) |
| Model access | LiteLLM proxy | LiteLLM proxy (unchanged, one `model_id` flip) |
| Product knowledge | Milvus vector RAG | Milvus vector RAG (unchanged) |
| Conversation memory | Milvus semantic recall | Amazon Bedrock AgentCore Memory |
| Business tools | MCP server on EKS | MCP server on EKS (unchanged) |
| Sandboxed execution | out of scope | AgentCore Code Interpreter + Browser |
| Multi-agent | A2A protocol | A2A protocol (unchanged) |
| Observability | Langfuse | Langfuse, dual-exported to AgentCore Observability |
| Evaluation | LLM-as-a-Judge via LiteLLM | AgentCore Evaluations (built-in + custom evaluator) |
| Knowledge graph | Neo4j | optional |

The point, proven twice: each capability is an independent decision. You do not pick "EKS plus open source" or "all managed" as a package. Pick per capability, keep orchestration where your operational strength is, and let the model plane absorb the backend choice so the agent never has to. The full argument: [docs/decision-framework.md](docs/decision-framework.md).

## The application

**AnyCompany Shop**, a fictional electronics retailer. The agent handles order status and tracking, product questions, inventory checks, returns, and light computation, through a Chainlit chat UI with four profiles (each track, single-agent and multi-agent). Test data: three orders, a 13-product catalogue with store FAQs, and stock levels for 10 products, all in [data/](data).

The agent gains one capability per stage, mirroring the workshop's labs:

```
agent loop + lookup_order          Strands, one tool, three hardcoded orders
observability                      Langfuse traces every call and decision
RAG                                product catalogue in Milvus
memory                             semantic recall (Milvus) or managed (AgentCore)
tools over MCP                     order/inventory/returns behind a protocol
multi-agent                        Order + Product specialists over A2A
evaluation                         LLM-as-a-Judge, both self-managed and managed
knowledge graph                    Neo4j for what vector search cannot answer
```

## Repository layout

```
app/agent/          Strands agent: one image, four entrypoints (single agent,
                    orchestrator, order specialist, product specialist)
app/mcp-server/     Shop tools over MCP: lookup_order, check_inventory, process_return
app/ui/             Chainlit chat UI with the four profiles
platform/           LiteLLM model plane, vLLM on Inferentia, Langfuse/Milvus/Neo4j installs
deploy/k8s/         Track manifests; the diff between the two agent manifests IS the migration
infra/terraform/    VPC, EKS Auto Mode, ECR, Pod Identity, evaluations log group
evaluation/         Both judges: Langfuse script and AgentCore Evaluations CLI
scripts/            env, build, deploy per track, data seeding, smoke tests, cleanup
docs/               architecture, both walkthroughs, decision framework, troubleshooting, costs
```

## Quickstart

Full detail in [docs/walkthrough-self-managed.md](docs/walkthrough-self-managed.md) and [docs/walkthrough-integrated.md](docs/walkthrough-integrated.md).

```bash
# 1. Infrastructure (about 25 minutes)
cd infra/terraform && terraform init && terraform apply

# 2. Build and deploy the platform
source scripts/env.sh
./scripts/build-and-push.sh
./scripts/deploy-platform.sh          # LiteLLM + Inferentia pool (+ vLLM if image set)
# Langfuse, Milvus, Neo4j: platform/*/README.md, then scripts/seed_data.py

# 3. Self-managed track
./scripts/deploy-self-managed.sh
./scripts/test-chat.sh

# 4. Integrated track: same image, managed backends
export AGENTCORE_MEMORY_ID=<memory resource id>
./scripts/deploy-integrated.sh

# 5. Score the conversations
python evaluation/langfuse_judge.py --limit 10          # self-managed judge
./evaluation/agentcore/create-evaluator.sh              # managed judge, once
./evaluation/agentcore/run-evaluation.sh                # per conversation
```

## Security model

- No static AWS credentials anywhere. EKS Pod Identity binds service accounts to scoped IAM roles.
- Only the LiteLLM service account can invoke Bedrock models. Agents cannot bypass the model plane.
- The agent service account holds AgentCore data-plane and trace-export permissions, nothing more.
- Sandboxed execution (code, browsing) happens in managed AgentCore sessions outside the cluster; the agent pod holds no execution rights of its own.
- The reference architecture puts Cognito or Keycloak in front of the UI; auth is deliberately out of scope in this lab build and the agents are ClusterIP-only.

## Findings I keep referring back to

1. **The gateway is the architecture.** Putting LiteLLM in front of inference on day one turned "which model, whose hardware" into a routing entry. The Qwen-to-Bedrock migration was one line, and it works in reverse, which is the honest answer to lock-in in both directions.
2. **A 3B model with good tools beats a bigger model without them** for a scoped job like retail support. Most of the agent's value came from `lookup_order`, RAG, and the graph, not the weights.
3. **Vector search and graphs answer different questions.** Similar is not related. The shop needed both Milvus and Neo4j, and the agent picks per question.
4. **What you can measure depends on what you emit.** The managed judge could verify grounding only because tool-call spans existed. Same judge, richer traces, higher scores. Instrumentation quality is evaluation quality.
5. **"Integrated" costs coordination but buys reversibility.** Running Kubernetes and managed services together is messier than either extreme, and still the track I would pick for a real team: the hard problems became API calls while the logic stayed debuggable in my own code.

## Costs and cleanup

The self-managed track's cost is capacity-shaped (the Inferentia node bills while it exists); the integrated track's is usage-shaped (Bedrock and AgentCore idle at zero). Details and teardown order: [docs/cost-and-cleanup.md](docs/cost-and-cleanup.md). Everything is destroyable with `./scripts/cleanup.sh`.

## Credits and provenance

- Built from the AWS [AI Agents on Amazon EKS](https://catalog.workshops.aws/ai-agents-on-eks/en-US) workshop; the lab structure, the AnyCompany Shop scenario, and the evaluation module's telemetry pattern follow it, reimplemented and documented here as my own build.
- Frameworks and services: [Strands Agents SDK](https://strandsagents.com/), [LiteLLM](https://litellm.ai/), [vLLM](https://vllm.ai/), [Langfuse](https://langfuse.com/), [Milvus](https://milvus.io/), [Neo4j](https://neo4j.com/), [Chainlit](https://chainlit.io/), [Model Context Protocol](https://modelcontextprotocol.io/), [A2A](https://a2a-protocol.org/), Amazon Bedrock and [AgentCore](https://aws.amazon.com/bedrock/agentcore/).

## License

MIT-0. See [LICENSE](LICENSE).
