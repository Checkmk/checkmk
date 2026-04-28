# cmk-agent-receiver

See [README.md](README.md) for architecture, API, configuration, and development workflows.

## Testing

Component tests offer two app-startup modes — pick based on what you're testing:

- **`TestClient`** (default fixture): in-process, fast, covers most endpoint logic
- **`AgentReceiverRunner`**: spawns a real Gunicorn process; required for anything involving mTLS or the `ClientCertWorker` certificate extraction
