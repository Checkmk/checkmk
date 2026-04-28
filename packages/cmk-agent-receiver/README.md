# cmk-agent-receiver

A [FastAPI](https://fastapi.tiangolo.com/) service that acts as the HTTP
endpoint through which Checkmk agents and relays communicate with a Checkmk
site.
It is started automatically by `omd start` and served via
[Gunicorn](https://gunicorn.org/) with a custom
[Uvicorn](https://www.uvicorn.org/) worker.

## Architecture

The package exposes a single main app (`cmk.agent_receiver.main:main_app`)
that mounts two independent FastAPI sub-applications:

| Sub-app            | Mount path               | Purpose                                                                                                       |
| ------------------ | ------------------------ | ------------------------------------------------------------------------------------------------------------- |
| **agent-receiver** | `/<site>/agent-receiver` | Agent registration & pairing, certificate signing / renewal, monitoring-data upload                           |
| **relay**          | `/<site>/relays`         | Relay registration, mTLS certificate exchange, task management, config activation, monitoring-data forwarding |

Shared functionality (configuration, authentication, certificates, logging,
B3 trace-ID middleware) lives in `cmk/agent_receiver/lib/`.

The relay sub-app is only active on editions that support relays.

### mTLS client certificate extraction

Agent and relay endpoints require mTLS authentication.
The custom `ClientCertWorker` (in `worker.py`) extends the Uvicorn worker to intercept H11 protocol frames during the TLS handshake, extract the client certificate's CN, and inject it as a `verified-uuid` HTTP header.
FastAPI endpoint dependencies then validate this header against the UUID in the URL path, preventing application-layer spoofing.

## API

The **agent-receiver** sub-app covers agent registration (including async approval workflows and legacy pairing), certificate renewal, monitoring-data upload, and registration status queries.
All endpoints that operate on a specific agent UUID require mTLS — the client certificate CN is validated against the UUID in the URL path.

The **relay** sub-app covers relay registration, certificate exchange, task management (create / fetch / update), config activation, and forwarding of monitoring data to CMC.
Relay tasks are stored in-memory with a configurable TTL and a bounded per-relay queue depth.
At startup the service schedules an asynchronous background task (with exponential-backoff retry) to push an initial relay config task — startup is not blocked while this completes.

The full endpoint list is available via FastAPI's auto-generated OpenAPI docs at `/<site>/agent-receiver/docs` and `/<site>/relays/docs` when running locally.

## Configuration

The service reads `agent_receiver_config.json` from `$OMD_ROOT` at startup.
If the file is absent, built-in defaults apply.

| Key                           | Type    | Default | Description                            |
| ----------------------------- | ------- | ------- | -------------------------------------- |
| `task_ttl`                    | `float` | `120.0` | Time-to-live for relay tasks (seconds) |
| `max_pending_tasks_per_relay` | `int`   | `10`    | Maximum pending tasks per relay        |

The environment variables `OMD_ROOT` and `OMD_SITE` must be set (provided automatically by `omd`).

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
