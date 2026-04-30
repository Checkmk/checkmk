# change_quality metric

Per-werk record of "did the introducing commit include a test file?",
written to `cmk_change_tested` in the QA Metabase postgres.

## Run modes

### Incremental — `make qa-metrics-change-quality`

Default. Reads `MAX(commit_time)` from `cmk_change_tested` for the current
branch and only walks commits newer than that. Daily / hourly re-runs take
seconds.

> **After changing the metric definition** (any of `walk.py`,
> `detect_test.py`, `components.py`, `rows.py`, …) the incremental mode will
> _not_ re-derive existing rows — it skips commits already in the DB. Run
> `make qa-metrics-change-quality-full` to rebuild every row under the new
> logic.

The script also prints this reminder to its INFO log on every incremental
run, so it's hard to forget.

### Full rebuild — `make qa-metrics-change-quality-full`

Ignores the watermark and walks all of git history. Re-derives every row
under the current code. Use this after every change to the metric
definition.

### Dry-run — `make qa-metrics-change-quality-dryrun`

Walks all of history, emits the CSV at
`$(REPO_PATH)/qa-metrics-change-quality.csv`, does not write to the DB.
Useful for inspecting rows before a real push.

## Env overrides (all targets)

```
QA_METRICS_REPO    # default: $(REPO_PATH)
QA_METRICS_BRANCH  # default: BRANCH_VERSION from <repo>/defines.make
QA_METRICS_FROM    # YYYY-MM-DD; explicit start, overrides watermark
QA_METRICS_TO      # YYYY-MM-DD
QA_METRICS_CHANGE_QUALITY_CSV  # default: <repo>/qa-metrics-change-quality.csv
```

## When to use which

| Situation                                                     | Target                             |
| ------------------------------------------------------------- | ---------------------------------- |
| New commits since last run, metric unchanged                  | `qa-metrics-change-quality`        |
| You edited `detect_test.py` / `components.py` / `walk.py` / … | `qa-metrics-change-quality-full`   |
| Want to inspect rows before pushing                           | `qa-metrics-change-quality-dryrun` |
