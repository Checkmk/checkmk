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
