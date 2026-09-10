# LiteLLM: the shared model plane

The single highest-leverage component in this architecture. Agents in both tracks call `http://litellm.litellm:4000` with the OpenAI API and a `model_name`. This proxy decides what that name means:

| model_name | Backend | Track |
|---|---|---|
| `qwen2-5-3b-neuron` | vLLM serving Qwen2.5-3B on Inferentia, in-cluster | Self-managed |
| `nova-lite` | Amazon Nova Lite on Bedrock | Integrated |
| `claude-sonnet-4-5` | Claude Sonnet 4.5 on Bedrock | Judge model for evaluation |

Moving an agent from self-hosted chips to Bedrock is therefore a one-line change to its `MODEL_ID` environment variable. The agent code, prompts, tools, tracing, and protocols are untouched. It also works in reverse, which is the honest answer to model lock-in in either direction.

Bedrock authentication: the `litellm` ServiceAccount is bound to an IAM role with `bedrock:InvokeModel` through EKS Pod Identity (see `infra/terraform/podidentity.tf`). No keys in the cluster.

```bash
envsubst < deployment.yaml | kubectl apply -f -
kubectl apply -f configmap.yaml
kubectl -n litellm rollout status deploy/litellm
```
