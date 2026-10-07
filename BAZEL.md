# Bazel Developer Reference

Quick reference for common developer workflows. Bazel is the primary build
system for unit tests, linting, formatting, and type checking. See
[CONTRIBUTING.md](CONTRIBUTING.md) for the full contribution guide and
the [Introduction to Bazel](https:de//wiki.lan.checkmk.net/spaces/DEV/pages/131340234/Introduction+to+Bazel)
wiki page for deeper background.
See [How to run Bazel](https://wiki.lan.checkmk.net/spaces/DEV/pages/131344788/How+to+run+Bazel)
for more in depth commands.

## Core subcommands

| Command      | What it does                                                                                                                              |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `bazel test` | Builds and executes test targets; reports pass/fail per test.                                                                             |
| `bazel run`  | Builds a single executable/script target and immediately runs it.                                                                         |
| `bazel lint` | Aspect-lint wrapper: enforces language rules, runs static analysis, and sorts Python imports; generates fix patches applied with `--fix`. |

## Quick start

Bazel is always run against a target.
A target is a folder containing a BUILD file which defines the parts of that target.

Targets in this repo are e.g. //tests/unit or //cmk/

```console
# Run all unit tests
$ bazel test //tests/unit/...

# Format files (layout only — does not sort imports)
$ bazel run //:format path/to/file.py

# Lint and autofix (includes import sorting)
$ bazel lint --fix //packages/cmk-ccc/...

# Type-check the whole repo with mypy
$ bazel build --config=mypy //...
```

## Running tests

### Unit tests

```console
# All unit tests
$ bazel test //tests/unit/...

# A specific package, with full output on failure
$ bazel test --test_output=errors //tests/unit/cmk/gui/...
```

### Edition-specific tests

Edition-aware targets are used when code is gated behind `--cmk_edition`.
Pass the flag to run all unit tests for that edition:

```console
$ bazel test --cmk_edition=pro //tests/unit/...
$ bazel test --cmk_edition=ultimate //tests/unit/...
```

For GUI tests that live under `nonfree/`, use the explicit targets:

```console
$ bazel test //tests/unit/cmk/gui/nonfree/pro:all
$ bazel test //tests/unit/cmk/gui/nonfree/ultimate:all
$ bazel test //tests/unit/editions/...
```

Available editions: `community`, `pro`, `ultimate`, `ultimatemt`, `cloud`.

### Integration, composition, and GUI E2E tests

These still use Make:

```console
$ tests/run_tests.sh test-system-singlesite
$ tests/run_tests.sh test-system-multisite
$ tests/run_tests.sh test-system-gui
```

## Formatting and linting

Formatting and linting are intentionally kept separate. Each step is predictable
and has no hidden side effects. This model applies consistently across all
supported languages.

### Formatting

```console
# Apply formatting to specific files
$ bazel run //:format path/to/file.py other/file.py

# Check formatting without modifying (CI-safe)
$ bazel run //:format.check path/to/file.py
```

Formatting **only** adjusts layout: whitespace, indentation, line breaks. It
does not enforce coding rules, run static analysis, or sort Python imports.

`//:format` handles multiple languages based on file extension (Python via ruff,
shell via shfmt, etc.).

prettier (JavaScript, TypeScript, Vue, JSON, Markdown, CSS, HTML) skips the
files it found formatted before and whose size and modification time are
unchanged. Its caches live in `.format_cache/`; delete that directory to make
prettier look at every file again.

### Linting

```console
# Lint a specific package
$ bazel lint //packages/cmk-ccc/...
$ bazel lint //packages/cmk-ccc:all

# Autofix where supported (applies ruff patches to the working tree)
$ bazel lint --fix //packages/cmk-ccc/...

# Lint the whole repo (slow on the first run)
$ bazel lint ...
```

Linting enforces language rules and best practices, runs static analysis, and
sorts Python imports. Import ordering is a linting concern in ruff, not a
formatting one — so if your imports are unsorted after `bazel run //:format`,
run `bazel lint --fix` next.

## Type checking (mypy)

mypy runs selectively on targets declared as `py_{library,binary,test}`.

```console
# Type-check a specific package
$ bazel build --config=mypy //packages/cmk-agent-based:all

# Type-check everything under cmk (edition-aware)
$ bazel build --config=mypy //cmk/...
```

## Key CLI flags

| Flag                    | Default        | Description                                          |
| ----------------------- | -------------- | ---------------------------------------------------- |
| `--cmk_edition=<ed>`    | `community`    | Edition: community, pro, ultimate, ultimatemt, cloud |
| `--cmk_version=<ver>`   | —              | Version string injected into builds                  |
| `--cmk_distro=<distro>` | `ubuntu-24.04` | Target Linux distribution                            |
| `--config=ci`           | off            | CI settings: no color, upload results, verbose fail  |
| `--config=debug`        | off            | Verbose output and gRPC stack traces                 |
| `--config=mypy`         | off            | Enable the mypy aspect for type checking             |
| `--config=mypy-gpl`     | off            | Like `--config=mypy`, but with `mypy-gpl.toml`       |
| `--test_output=errors`  | `summary`      | Show full test output only on failures               |

## Resource usage on developer machines

The repository ships defaults which keep a developer machine usable while Bazel
builds. They live in `bazel/rc/` and apply to every worktree without any setup.

`--config=ci` overrides the resource limits with values matching the CI pods
(see `bazel/rc/ci.rc`); CI disables the disk cache in `/etc/ci.bazelrc`.

### What the limits do

- **CPU** is the effective knob: most actions declare one CPU, so
  `--local_resources=cpu=HOST_CPUS-2` limits how many actions run locally at the
  same time and leaves two CPUs to the desktop. `HOST_CPUS` counts hardware
  threads (not physical cores), or the CPU limit of a container.
- **Memory** stays at Bazel's default of `HOST_RAM*.67`. It is only checked
  against the RAM each action declares, which is an estimate for most actions.
  The Bazel server, persistent workers (e.g. tsc, mypy) and tests that use more
  than declared are not counted, so a lower limit would not reliably prevent
  swapping or OOM kills.
- **Workers** stay at Bazel's default of 4 per worker kind (mnemonic). Worker
  actions also wait for free CPUs, so more workers would only add resident
  memory.
- Tools which run several threads per action (e.g. rustc, linkers) can still use
  more CPUs than the limit suggests.

### Disk usage

Bazel keeps several caches below `~/.cache`:

| Path                                  | Bounded by                                                     |
| ------------------------------------- | -------------------------------------------------------------- |
| `~/.cache/bazel_disk_cache/`          | 30G, collected in the background once the Bazel server is idle |
| `~/.cache/bazel/repo_contents_cache/` | entries unused for 14 days are collected                       |
| `~/.cache/bazel/_bazel_$USER/<hash>/` | nothing: one output base per worktree                          |

### Personal overrides

Put options for all worktrees into `~/.bazelrc` and options for a single
worktree into `user.bazelrc` in its root (not tracked by git). Both are read
after the repository defaults, so their values win.

Further options to try if the machine still becomes unresponsive:

```
# Run the Bazel server with lower CPU and IO priority
startup --batch_cpu_scheduling
startup --io_nice_level=7

# Cap the heap of the Bazel server
startup --host_jvm_args=-Xmx4g

# Schedule local actions based on the actual CPU load instead of declared costs
# (experimental, used on CI)
common --experimental_cpu_load_scheduling

# Fewer threads for loading and analysis
common --loading_phase_threads=HOST_CPUS*.5
```
