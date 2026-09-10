# Choosing where agents run

Three strategies for agentic AI on AWS, and the questions that separate them. Condensed and adapted from the workshop's strategy module, with my own reading added.

## The three strategies

**1. Self-managed on Kubernetes.** Open-source models on EKS with full control of every layer: vLLM for serving, Strands for the agent, Milvus for vectors, Langfuse for observability, MCP and A2A for protocols. Maximum flexibility and portability, maximum operational responsibility. Fits teams with specific model requirements, strict data residency, or existing Kubernetes muscle.

**2. Integrated: self-hosted agents, managed capabilities.** The agent framework and orchestration stay in your code on EKS; infrastructure-heavy backends swap to managed services: Bedrock for inference, AgentCore for memory and sandboxed tools. Same agent code, different config. Fits teams that want to own the logic but not the GPU fleet.

**3. Fully managed.** Bedrock end to end, including agent orchestration. Fastest to production, least to operate, least control, and the orchestration logic is the hardest to debug of the three. Fits teams shipping fast on Bedrock models.

## The framework

| Question | Self-managed | Integrated | Fully managed |
|---|---|---|---|
| Need a specific open-source model? | Yes | No | No |
| Kubernetes expertise on the team? | Required | Required | Not required |
| Data must stay in your VPC? | Yes | Partial | Partial |
| Time to production matters most? | Slow | Middle | Best |
| Cloud-portable architecture wanted? | Yes | Partial | No |
| Complex multi-agent workflows? | Full control | Full control | Limited |

## My reading, having built the first two

The framework looks like a menu of three packages. Building both tracks showed me it is not. The real unit of decision is the capability, not the strategy:

- Inference can be managed while memory stays self-hosted, or the reverse.
- The protocols (MCP, A2A) and the observability layer do not care where backends live.
- A model gateway (LiteLLM here) turns the inference decision into a routing entry, reversible in either direction.

So the practical advice is: pick per capability, keep orchestration where your operational strength is, and invest early in the two things that survive every migration, the protocol boundaries and the traces. The strategy table is where the conversation starts, not where it ends.

One more honest note: "integrated" is also the operationally messiest of the three, because you run Kubernetes AND consume managed services, and AgentCore service availability is region-dependent. The flexibility has a coordination cost. It was still the track I would choose for a real team, because it converts the hardest problems (GPU fleets, sandbox isolation, evaluation plumbing) into API calls while keeping the logic debuggable.
