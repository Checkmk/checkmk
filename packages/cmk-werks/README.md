# cmk-werks

Tools for managing Checkmk werks (changelog entries).
Contains the `cmk.werks` namespace and the `cmk.werk_ids_server` HTTP service that allocates werk IDs centrally.

## cmk.werks.tool — library and CLI

`cmk.werks.tool` provides the `werk` CLI plus werk parsing, validation, formatting, and ID management.

Run `werk status` to check your werk ID setup: which reservation workflow is active, whether the werk ID server is reachable and your secret still accepted, how many IDs you have reserved, and anything that would make `werk new` fail. It is read-only, exits non-zero when it found problems, and still prints the full picture in states where other commands refuse to run.

`werk status --json` prints the same information as a single JSON document on stdout — typed values and stable keys, with every section always present:

```sh
werk status --json | jq -r '.problems[] | "\(.item): \(.fix)"'
```

`schema_version` is bumped whenever the document changes shape.

## cmk.werks.site — site runtime helpers

`cmk.werks.site` contains the werk handling used inside a Checkmk site (e.g. werk acknowledgement storage).

## cmk.werk_ids_server — werk ID server

A small Flask/Gunicorn HTTP service that hands out unique, monotonically increasing werk IDs.
It stores a single counter in a SQLite database and exposes three endpoints:

| Method | Path       | Auth   | Description        |
| ------ | ---------- | ------ | ------------------ |
| `GET`  | `/`        | —      | Health check       |
| `GET`  | `/connect` | Bearer | Connectivity check |
| `POST` | `/reserve` | Bearer | Reserve werk IDs   |

The `/reserve` endpoint accepts `{"local_werk_ids_count": N}` and tops up to 10 IDs:

```json
POST /reserve
Authorization: Bearer <secret>
{"local_werk_ids_count": 3}

→ {"reserved_werk_ids": [22225, 22226, 22227]}
```

The secret is read from `/etc/cmk-werk-ids/secret` on every authenticated request, so rotating the file takes effect immediately without a service restart.

### First-time install

Prerequisites:

- **Local**: `bazel`, `rsync`, and `python3` in `PATH`
- **Remote**: `python3` available
- **Remote**: `root` user reachable via SSH (passwordless key auth)
- **Remote**: `/etc/cmk-werk-ids/secret` must exist before running install

```sh
python3 packages/cmk-werks/scripts/werk_ids_server.py install [user@host]
```

Omitting `user@host` defaults to `root@werk-ids.lan.checkmk.net`.

The install step is idempotent: re-running it is safe and converges to the same end state.

This command:

1. Builds the server wheel and syncs it to the remote
2. Creates the `cmk-werk-ids` system user (used by the systemd unit to run gunicorn)
3. Installs `python3.12-venv` if missing, then creates a virtualenv at `/opt/cmk-werk-ids/venv` and installs the wheel
4. Installs and enables the systemd socket and service

The database is initialised automatically on first start of the service.

### Deploy (update existing installation)

Prerequisites: `root` user reachable via SSH (passwordless key auth).

```sh
python3 packages/cmk-werks/scripts/werk_ids_server.py deploy [user@host]
```

Rebuilds the wheel, syncs it, reinstalls into the existing virtualenv, and restarts the service.

### Dry run

Both commands accept `--dry-run` to print every SSH and rsync call without executing anything:

```sh
python3 packages/cmk-werks/scripts/werk_ids_server.py --dry-run install
python3 packages/cmk-werks/scripts/werk_ids_server.py --dry-run deploy [user@host]
```

## Development

```sh
# Run all tests
bazel test //packages/cmk-werks:all

# Format
bazel run //:format packages/cmk-werks

# Lint
bazel lint //packages/cmk-werks:all

# Type-check
bazel build --config=mypy //packages/cmk-werks:all
```
