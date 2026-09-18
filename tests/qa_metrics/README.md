# tests/qa_metrics

Tree of QA metrics that aggregate something about the check_mk codebase and
push the result to the QA Metabase postgres for dashboarding.

## Layout

- `db/` — shared library: psycopg connection (env / SSL fallback),
  `upsert_record`, `apply_schema_file`, and a `Table[RowT]` binding from
  row dataclass to postgres table. Every metric depends on this.
- `components/` — shared library: resolves repository paths to the components
  that own them, reading the `OWNERS` files through Gerrit's code-owners API.
  Ownership reflects the remote branch, not the local checkout, and data that
  attributes nothing is refused rather than returned.
- `change_quality/` — first metric. Per-werk row of "did the introducing
  commit include a test?", written to `cmk_change_tested`.
- `test_coverage/` — Python test coverage. Uploads overall coverage history to
  `cmk_code_coverage_total` and the latest per-module breakdown to
  `cmk_code_coverage_per_module`. Two entry points over the definitions in
  `common.sh`: `repository.sh` measures the whole repository and is what the nightly
  runs, `component.sh <component-id>` measures one component locally and never
  uploads. See `component.sh --help` for its options.

## Adding a new metric

1. Create `tests/qa_metrics/<metric>/` with a `schema.sql`, a row dataclass,
   a `push.py` CLI, and a `BUILD` file.
2. `from tests.qa_metrics.db import MetabasePostgres, upsert_record, apply_schema_file`.
3. Mirror the data flow: build rows → `with MetabasePostgres.from_env() as db: ... upsert_record(...)`.

## Environment

The lib reads its connection from these env vars (used by every metric):

- `POSTGRES_HOST`, `POSTGRES_PORT` (default 5432), `POSTGRES_DB`, `QA_POSTGRES_USER` — required.
- Auth: `QA_POSTGRES_PASSWORD` _or_ the SSL trio
  `QA_POSTGRES_SSLROOTCERT` / `QA_POSTGRES_SSLCERT` / `QA_POSTGRES_SSLKEY`
  (with `QA_POSTGRES_SSLMODE`, default `allow`).

## Build & test

All checks go through bazel. Run from the repo root:

```bash
# Unit tests
bazel test //tests/unit/qa_metrics/...

```

Per-target test invocations:

```bash
bazel test //tests/unit/qa_metrics/db:db                            # shared-lib tests
bazel test //tests/unit/qa_metrics/components:tests                 # ownership shared-lib tests
bazel test //tests/unit/qa_metrics/change_quality:change_quality    # change-quality metric tests
bazel test //tests/unit/qa_metrics/test_coverage:tests              # code-coverage metric tests
```

The change-quality test target opts out of the bazel sandbox (`tags =
["no-sandbox"]`) because `test_walk.py` shells out to the host `git` binary
against a fixture repo built in `tmp_path`.
