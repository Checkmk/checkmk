# Database endpoints

Two environment variables select the databases under test. The plugin doesn't
distinguish "local" from "remote" — it's a TCP connection either way, so
neither variable is tied to where the target actually lives:

| Variable          | Required | Meaning                                                                                                                                                                                 |
| ----------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `CI_ORA2_DB_TEST` | Yes      | Mandatory reference endpoint; the suite unwraps it and treats it as `WORKING_ENDPOINTS[0]`.                                                                                             |
| `CI_ORA1_DB_TEST` | No       | Optional second endpoint with its own credentials (e.g. sys/sysdba). The endpoint-iterating tests include it when set; the explicit-sysdba test requires it and skips itself otherwise. |

Both use the same colon-separated connection string, parsed by `SqlDbEndpoint::from_str`:

```
host:user:password:port:instance_name:role:service_name:sid:_:_
```

| Field               | Notes                                                                                                                                                                                       |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `host`              | DNS name or IP.                                                                                                                                                                             |
| `user` / `password` | DB credentials. May be left empty to reuse the previous endpoint's credentials.                                                                                                             |
| `port`              | Listener port (default `1521`).                                                                                                                                                             |
| `instance_name`     | `_` or empty → `None`. Used to verify the plugin identifies the instance.                                                                                                                   |
| `role`              | e.g. `sysdba`; empty → none. Always explicit — nothing infers a role from the host (e.g. connecting as `sys` needs `role: sysdba` spelled out; Oracle refuses `sys` without it, ORA-28009). |
| `service_name`      | Mandatory for connection.                                                                                                                                                                   |
| `sid`               | `_` or empty → `None`.                                                                                                                                                                      |

Point `CI_ORA2_DB_TEST` at any reachable database — no other file needs editing for a local run.
CI delivers only a password, so `CI_ORA2_DB_TEST` is constructed from it in the run scripts and the Jenkins jobs.

> Never commit a connection string containing credentials.
> Build the string from a password held in an environment variable or a `0600` file outside the checkout.
