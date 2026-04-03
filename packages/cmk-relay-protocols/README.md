# cmk-relay-protocols

Shared Pydantic data models and protocol definitions for Checkmk's relay system.
This package is the contract layer between the relay engine, the agent receiver, and the Checkmk site.

## Modules

| Module                                | Purpose                                                          |
| ------------------------------------- | ---------------------------------------------------------------- |
| `cmk.relay_protocols.configuration`   | Engine config: hosts, services, schedules, fetcher settings      |
| `cmk.relay_protocols.relays`          | Relay lifecycle: registration, certificate rotation, relay state |
| `cmk.relay_protocols.tasks`           | Task protocol: ad-hoc fetch tasks and relay config distribution  |
| `cmk.relay_protocols.monitoring_data` | Monitoring result payloads sent from relays to the site          |

All models use Pydantic v2. Request/response models are frozen (immutable).

## Development

```bash
bazel test //packages/cmk-relay-protocols:unit
bazel run //:format packages/cmk-relay-protocols
bazel lint //packages/cmk-relay-protocols/...
bazel build --config=mypy //packages/cmk-relay-protocols:cmk-relay-protocols
```

Deploy to a local site: `./.f12`
