# Model serving: vLLM + Qwen2.5-3B on AWS Inferentia

The self-managed track's inference layer. Qwen2.5-3B-Instruct is served by vLLM on an `inf2` (AWS Inferentia2) node, compiled through the Neuron SDK. Agents never call it directly; LiteLLM fronts it as `qwen2-5-3b-neuron`.

Why this shape:

- **Inferentia over GPU** for cost-efficient inference on a small open model. The NodePool provisions `inf2` on demand and scales to zero when the deployment is removed.
- **vLLM** provides the OpenAI-compatible `/v1` API LiteLLM expects, plus continuous batching.
- **A 3B model is the point, not a compromise.** For a tool-calling customer service agent, most of the intelligence lives in the tools and retrieval. The workshop demonstrates that deliberately.

```bash
kubectl apply -f nodepool-inferentia.yaml
export VLLM_NEURON_IMAGE=<current vLLM Neuron image>   # see AWS Neuron DLC releases
envsubst < qwen25-3b-neuron.yaml | kubectl apply -f -
kubectl -n vllm rollout status deploy/qwen2-5-3b-neuron --timeout=900s
```

First start is slow: node provisioning plus model download and Neuron compilation. Expect several minutes. Verify:

```bash
kubectl -n vllm port-forward svc/qwen2-5-3b-neuron 8000:8000 &
curl -s localhost:8000/v1/models | jq
```
