# cmk-trace

## Overview

The package is a thin convenience layer on top of `opentelemetry-api` / `opentelemetry-sdk` and the OTLP gRPC exporter.
It re-exports the OTel symbols Checkmk code uses (`Span`, `SpanKind`, `Status`, `TracerProvider`, ...) so callers do not depend on `opentelemetry.*` directly.

Public surface, grouped by module:

- `cmk.trace` — application bootstrap and the `Tracer` facade.
  `init_tracing(...)` builds a `TracerProvider` populated with the standard `service.name` / `service.namespace` / `service.instance.id` / `host.name` resource attributes and registers it as the global provider.
  `get_tracer(name)` returns a `Tracer` wrapper.
  `resource_attributes_from_config(omd_root)` reads optional extra attributes from `etc/omd/resource_attributes_from_config.json`.
- `cmk.trace.export` — `exporter_from_config(level, config)` builds an `OTLPSpanExporter` (gRPC) for the configured target or returns `None` when tracing is disabled. `init_span_processor(provider, exporter)` attaches a `BatchSpanProcessor` to a provider.
- `cmk.trace.logs` — `add_span_log_handler()` installs a root logging handler that attaches log records to the active span as events. Workaround for Jaeger not supporting OTel logs natively.

## Configuration

Tracing is driven by OMD site config keys (read from `etc/omd/site.conf` by callers and passed in as a `Mapping[str, str]`):

| Key                              | Effect                                                                                                          |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `CONFIG_TRACE_SEND`              | `on` enables span export; anything else disables it.                                                            |
| `CONFIG_TRACE_SEND_TARGET`       | `local_site` (default) sends to `localhost:CONFIG_TRACE_RECEIVE_PORT`; otherwise an explicit OTLP endpoint URL. |
| `CONFIG_TRACE_RECEIVE_PORT`      | Port used together with `local_site`.                                                                           |
| `CONFIG_TRACE_SERVICE_NAMESPACE` | Overrides the default namespace passed to `service_namespace_from_config`.                                      |

Extra resource attributes can be supplied via the JSON file `$OMD_ROOT/etc/omd/resource_attributes_from_config.json` (a flat string-to-string mapping). Missing or unreadable file is treated as no extra attributes.

## Usage

Bootstrap once at process startup, ideally before any span is created:

```python
import logging
from cmk import trace
from cmk.trace.export import exporter_from_config, init_span_processor
from cmk.trace.logs import add_span_log_handler

omd_config = get_omd_config(omd_root)  # provided by the caller

init_span_processor(
    trace.init_tracing(
        service_namespace=trace.service_namespace_from_config("", omd_config),
        service_name="my-service",
        service_instance_id=omd_site(),
        extra_resource_attributes=trace.resource_attributes_from_config(omd_root),
    ),
    exporter_from_config(
        exporter_log_level=logging.CRITICAL,
        config=trace.trace_send_config(omd_config),
    ),
)
add_span_log_handler()
```

Create spans with the `Tracer` facade:

```python
from cmk import trace

tracer = trace.get_tracer()

with tracer.span("handle-request", attributes={"request.id": req_id}):
    do_work()

@tracer.instrument()
def do_work() -> None:
    ...
```

Propagate context to a child process:

```python
from cmk import trace

env = {**os.environ, **trace.context_for_environment()}
subprocess.run([...], env=env)

# In the child:
ctx = trace.extract_context_from_environment(os.environ)
with trace.get_tracer().span("child", context=ctx):
    ...
```
