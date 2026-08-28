# Migration input corpus (CMK-38008)

Representative legacy `mk_oracle.cfg` files, round-tripped through the
migrator by `test_migrate_input_corpus` in `tests/test_mk_oracle_bin.rs`.

Each case covers one dimension observed in the UAT migration bugs under
epic CMK-37271 (auth variants, remote instances, `SQLS_*` combinations,
formatting quirks, `mk_oracle.d` multi-file) — one dimension per case,
not the full cross product.

## Layout

Each case is a pair of input and expected migrator output (golden file):

- `NN_<case>.cfg` + `NN_<case>.yaml` — a single-file legacy config and
  the output it must migrate to
- `NN_<case>/` — a multi-file case: `main.cfg` plus a `mk_oracle.d/`
  directory passed via `--migrate-subdir`, with the golden file at
  `NN_<case>/expected.yaml`

## Comparison

The golden file holds the migrator's full stdout, normalized to be
deterministic:

- the `# --- Converted from <path> at <timestamp> ---` header line is
  dropped (path and timestamp vary)
- the lines of the `Known environment variables` comment block are
  sorted (their order is HashMap iteration order)

Warnings (`# WARNING:` lines) and the generated YAML are compared
verbatim. Additionally, every case asserts that the output stays
loadable via the plugin's own config loader.

## Updating the golden files

After an intended migrator change, regenerate with cargo (Bazel runs
the test in a sandbox, so the update mode only works via cargo):

```
cd packages/mk-oracle
MK_ORACLE_UPDATE_CORPUS=1 cargo test --test test_mk_oracle_bin migration_corpus
```

Then review the golden-file diff — it is the user-visible behavior
change of the migrator.

## Cases for open bugs

Cases named `NN_open_<ticket>_*` encode the _expected_ behavior of
migration bugs that are not fixed yet (their golden files are written
by hand), so they fail on purpose until the fix lands. When a ticket is
resolved, regenerate the golden and review the diff; if the ticket is
rejected instead, remove the case or regenerate it to the agreed
behavior, recording the rationale in the ticket.

## Deliberately not covered

- Windows `.ps1` dialect: the corpus is shell syntax, the test runs on
  non-Windows only; the ps1 migration path is exercised by the
  `references/output-*.ps1` tests.
- Every auth × SQLS × quirk combination: per the ticket, each dimension
  is exercised on its own.
