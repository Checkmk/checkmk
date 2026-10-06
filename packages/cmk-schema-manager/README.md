# cmk-schema-manager

Lets any component manage its own database schema over time. A revision is an
id plus an upgrade method; a `RevisionChain` is their ordered history.

A component declares a `ManagedDatabase` under the `cmk.schema_migrations`
plugin namespace. Its `name` identifies the database, `backend` is the kind
of database (SQLite), `chain` its revisions. `omd_lifecycle` lists the omd
events at which pending revisions are applied: `create` for `omd create`,
`update` for `omd update`.
