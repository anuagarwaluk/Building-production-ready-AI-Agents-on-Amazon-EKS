# Observability: Langfuse

Langfuse traces every LLM call, tool invocation, and agent decision as OpenTelemetry spans. It is deliberately installed before RAG, memory, or multi-agent labs: once systems have more than one moving part, you debug with traces or you guess.

Both tracks reuse the same Langfuse. When the integrated evaluation module needs spans in AgentCore Observability too, the agent dual-exports rather than switching (see `app/agent/src/telemetry.py`), so this view never degrades.

## Install (official Helm chart)

```bash
helm repo add langfuse https://langfuse.github.io/langfuse-k8s
helm repo update
kubectl create namespace langfuse
helm install langfuse langfuse/langfuse -n langfuse \
  --set langfuse.salt.value=$(openssl rand -hex 16) \
  --set langfuse.nextauth.secret.value=$(openssl rand -hex 16) \
  --set postgresql.auth.password=$(openssl rand -hex 12)
kubectl -n langfuse rollout status deploy/langfuse-web --timeout=600s
```

Then open the UI, create an organisation and a project named `AnyCompany Shop`, and copy the project's public and secret keys into the agent deployment env (`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL=http://langfuse-web.langfuse:3000`).

```bash
kubectl -n langfuse port-forward svc/langfuse-web 3000:3000
```

Chart values evolve; check the langfuse-k8s repo for the current required secrets if the install complains.
