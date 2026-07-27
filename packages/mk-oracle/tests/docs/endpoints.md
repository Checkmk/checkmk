# Database endpoints

Two environment variables select the databases under test:

| Variable          | Required | Meaning                                                                                    |
| ----------------- | -------- | ------------------------------------------------------------------------------------------ |
| `CI_ORA2_DB_TEST` | Yes      | External reference endpoint; the suite unwraps it and treats it as `WORKING_ENDPOINTS[0]`. |
| `CI_ORA1_DB_TEST` | No       | Local endpoint; when set, local-connection tests run, otherwise they are skipped.          |

Both use the same colon-separated connection string, parsed by `SqlDbEndpoint::from_str`:

```
host:user:password:port:instance_name:role:service_name:sid:_:_
```

| Field               | Notes                                                                                                         |
| ------------------- | ------------------------------------------------------------------------------------------------------------- |
| `host`              | DNS name or IP.                                                                                               |
| `user` / `password` | DB credentials. May be left empty to reuse the previous endpoint's credentials.                               |
| `port`              | Listener port (default `1521`).                                                                               |
| `instance_name`     | `_` or empty → `None`. Used to verify the plugin identifies the instance.                                     |
| `role`              | e.g. `sysdba`; empty → none. `localhost` endpoints connect as `sysdba` automatically (see `common/tools.rs`). |
| `service_name`      | Mandatory for connection.                                                                                     |
| `sid`               | `_` or empty → `None`.                                                                                        |

`../files/endpoints.txt` lists the endpoints to load.
It references `$CI_ORA2_DB_TEST` only, so pointing that variable at any reachable database is sufficient — no edits to the file are needed for a local run.
CI delivers only a password, so `CI_ORA2_DB_TEST` is constructed from it in the run scripts and the Jenkins jobs.

> Never commit a connection string containing credentials.
> Build the string from a password held in an environment variable or a `0600` file outside the checkout.
