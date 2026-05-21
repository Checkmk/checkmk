# cmk-werks

Tools for managing Checkmk werks (changelog entries).
Contains the `cmk.werks` library and CLI used across the repo, and the `cmk.werk_ids_server` HTTP service that allocates werk IDs centrally.

## cmk.werks — library and CLI

`cmk.werks` provides werk parsing, validation, formatting, and ID management.

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
