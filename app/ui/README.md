# Chat UI

A Chainlit web UI with a profile dropdown holding four entries, one per combination of track (self-managed, integrated) and mode (single-agent, multi-agent). All profiles send the same `/chat` request; the profile only decides which Kubernetes Service receives it.

```bash
# Local run against a port-forwarded agent
SELF_MANAGED_AGENT_URL=http://localhost:8000 chainlit run app.py
```
