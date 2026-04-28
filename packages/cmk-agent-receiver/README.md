# Agent Receiver Package

Setup for using/testing agent-receiver package

agent-receiver server is running in your site after omd start.
If you want to apply local changes:
position yourself in cmk-agent-receiver directory
f12

If you want to debug agent-receiver it's useful to run an uvicorn worker from the command line:
omd stop agent-receiver
uvicorn cmk.agent_receiver.server:app

## Configuration

### Relay Configuration

The agent-receiver relay can be configured using a `relay_config.json` file. The configuration supports the following options:

- `task_ttl` (float): Time-to-live for tasks in seconds. Default: 120.0
- `max_tasks_per_relay` (int): Maximum number of tasks per relay. Default: 1000

#### Example Configuration

Create a `relay_config.json` file with the following content:

```json
{
  "task_ttl": 120.0,
  "max_tasks_per_relay": 1000
}
```

If the configuration file doesn't exist, default values will be used. See `relay_config.json.example` for a template.

## Testing

The component tests have two ways to start the agent receiver: use the real process if you are verifying TLS authorization.
The `TestClient` fixture (default in `conftest.py`) wraps the FastAPI app in-process using Starlette's test client — fast and suitable for most endpoint logic.
`AgentReceiverRunner` spawns a real Gunicorn process with the `ClientCertWorker`, enabling genuine mTLS handshakes and `verified-uuid` header injection; use it when testing certificate extraction or TLS-gated endpoints.

## Development

### Running locally for debugging

```bash
omd stop agent-receiver
uvicorn cmk.agent_receiver.main:main_app
```

<!-- CONTEXT
The main FastAPI app (main.py) mounts two distinct sub-apps:
  - agent-receiver (/<site>/agent-receiver) — handles agent registration, pairing, certificate renewal, and monitoring-data ingestion from Checkmk agents.
  - relay (/<site>/relays) — manages relay registration, task distribution, configuration activation, and forwarding of monitoring data from relays.
Both sub-apps share common library code under lib/.
The relay lifespan (startup logic) is defined on the main app because FastAPI does not propagate lifespan events to mounted sub-apps.
-->
