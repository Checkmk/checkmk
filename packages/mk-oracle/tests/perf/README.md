# Oracle Performance Benchmark

Measures wall-clock time of mk-oracle (Rust) vs the legacy mk_oracle bash plugin
across three database states: empty, seeded, and under Swingbench load.

## Prerequisites

Run `install.sh` once to check dependencies and pre-build mk-oracle:

```bash
./install.sh
```

Requires: Docker, Bazel, Java (for load testing), unzip.

## Quick start

```bash
export PERF_DB_PASSWORD=<your-password>   # required — no default
./setup.py up          # start Oracle container, seed tablespaces/jobs, run RMAN cycles
./measure.py           # standard scenario, 3 runs against current DB
./setup.py down
```

## Full load benchmark

`bench-phases.py` is the main load test runner. It manages the container
lifecycle, seeds all data, starts Swingbench, and runs measurements across three
phases automatically:

| Phase  | DB state                             | Results labelled      |
| ------ | ------------------------------------ | --------------------- |
| empty  | fresh container, no data             | `empty_standard.csv`  |
| seeded | 100 tablespaces + 500 jobs + RMAN    | `seeded_standard.csv` |
| load   | seeded + charbench (N virtual users) | `load_standard.csv`   |

```bash
./bench-phases.py                                   # standard + batched, 5 runs, 50 VU
./bench-phases.py --runs 3                          # faster
./bench-phases.py --uc 30                           # lighter load (recommended — 50 VU can stall the DB)
./bench-phases.py --no-use-legacy                   # skip legacy plugin
./bench-phases.py --scenarios batched               # single scenario
./bench-phases.py --uc 30 --sleep-between-runs 2    # lighter load + settle time
```

Results land in `runs/<prefix_session>/` — logs and CSVs together in one directory per run.

## Scripts

### `setup.py` — container and seed management

```bash
./setup.py up                    # start container, seed tablespaces/jobs, run RMAN cycles
./setup.py up --runs 5           # 5 RMAN backup cycles instead of 3
./setup.py up --no-seed          # start container only (used by bench-phases.py phase 1)
./setup.py seed-data             # seed 100 tablespaces + 500 scheduler jobs
./setup.py seed-rman [--runs 3]  # enable ARCHIVELOG + run RMAN backup cycles
./setup.py down                  # stop container
./setup.py down --volumes        # full teardown including data volume
```

Connection details written to `.env` after `up` — `measure.py` reads these automatically.

### `measure.py` — single measurement run

Runs one or more scenarios against the current DB and writes a CSV to `runs/`.

```bash
./measure.py                                    # standard, 3 runs
./measure.py --scenario batched --runs 5
./measure.py --no-use-legacy                    # skip legacy plugin
./measure.py --sleep-between-runs 2             # sleep 2s between invocations (reduces variance under load)
```

Scenarios:

| Scenario   | What it measures                                             |
| ---------- | ------------------------------------------------------------ |
| `standard` | Each of 17 sections timed individually (one invocation each) |
| `batched`  | All 17 sections in a single invocation                       |

### `bench-phases.py` — full three-phase benchmark

Orchestrates the complete empty → seeded → load test cycle. This is the script
to run for a full load test — it calls `setup.py` and `measure.py` internally.
See **Full load benchmark** above.

## Connection details

| Setting  | Variable           | Default   |
| -------- | ------------------ | --------- |
| Host     | `PERF_DB_HOST`     | localhost |
| Port     | `PERF_DB_PORT`     | 15210     |
| Service  | `PERF_DB_SERVICE`  | FREEPDB1  |
| User     | `PERF_DB_USER`     | system    |
| Password | `PERF_DB_PASSWORD` | _(none)_  |

`PERF_DB_PASSWORD` is required and has no default. Set it before running `setup.py up`
or sourcing `.env.docker` / `.env.drcp`. It is used both to initialise the Oracle
container and to connect to the database.

`install.sh` resolves and writes `MK_ORACLE_BIN` and `OCI_LIB_DIR` to `.env`
automatically after building.

## DRCP (Database Resident Connection Pooling)

`setup.py up` starts the DRCP pool automatically, but `measure.py` uses a
direct dedicated connection by default. To opt in, create a `tns/` directory
with the alias and point `PERF_TNS_DIR` at it:

```bash
mkdir -p tns
```

`tns/tnsnames.ora`:

```
PERF_POOLED =
  (DESCRIPTION =
    (ADDRESS = (PROTOCOL = TCP)(HOST = localhost)(PORT = 15210))
    (CONNECT_DATA =
      (SERVER = POOLED)
      (SERVICE_NAME = FREEPDB1)
    )
  )
```

`tns/sqlnet.ora`:

```
NAMES.DIRECTORY_PATH = (TNSNAMES)
```

Then add to `.env` (or export before running):

```bash
export PERF_TNS_DIR=/path/to/packages/mk-oracle/tests/perf/tns
```

`measure.py` reads `PERF_TNS_DIR` on startup; if set, it uses the `PERF_POOLED`
alias instead of a direct hostname/port connection.

## Results

Each run creates `runs/<prefix_session>/` containing both logs and CSVs.
CSV columns: `timestamp, run, scenario, section, plugin, wall_ms`.

## Load testing notes

- **30 VU is recommended** over the default 50 — the Docker Oracle Free container
  has a 2GB SGA limit, and 50 VU can exhaust the buffer cache or stall on redo log
  switches, causing TPS to drop to zero and producing artificially fast query times.
- Watch for stalls: if `measure.py` Rust times are under 20ms for all sections,
  the DB is likely idle despite charbench running. Check with:
  ```bash
  docker exec oracle-perf bash -c "echo 'SELECT event, COUNT(*) FROM v\$session WHERE wait_class != '"'"'Idle'"'"' GROUP BY event ORDER BY 2 DESC FETCH FIRST 5 ROWS ONLY; EXIT;' | sqlplus -s / as sysdba"
  ```
- Use `--sleep-between-runs 2` when measuring under load to give Oracle time to
  drain cursors between invocations and reduce run-to-run variance.
