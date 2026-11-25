# Bazel Developer Reference

This file maps developer workflows to the Bazel commands of this repository.
Don't run `pytest`, `ruff`, `mypy`, `cargo` or `vitest` directly: they bypass
the pinned tool versions and the environment that CI uses. The internal
[Introduction to Bazel](https://checkmk-int.atlassian.net/wiki/x/6IRlD) wiki
page explains the concepts.

Commands take either files or targets:

- `bazel run //:format` and `bazel run //:format.check` take file paths, or
  `--delta` for the files you changed.
- `bazel build`, `bazel test`, `bazel lint` and `bazel query` take targets: a
  single target (`//packages/cmk-ccc:unit`), all targets of a package
  (`//packages/cmk-ccc:all`), or a package and all packages below it
  (`//packages/cmk-ccc/...`). A package is a directory with a `BUILD` file.

Scope them to your change and leave `//...` to CI.

## Formatting

| I want to …                                  | Command                                |
| -------------------------------------------- | -------------------------------------- |
| Format the files I changed                   | `bazel run //:format -- --delta`       |
| Format specific files                        | `bazel run //:format -- <files>`       |
| Check the files I changed                    | `bazel run //:format.check -- --delta` |
| Apply buildifier's lint fixes to Bazel files | `bazel run //:buildifier`              |

- `--delta` selects the files changed since your branch split off
  `origin/master` (`origin/<branch>` on a stable branch), uncommitted and
  untracked ones included.
- Without arguments, `//:format` formats the whole repository.
- Formatting doesn't sort Python imports; `bazel lint --fix` does.
- prettier skips files it found formatted before unless their size or
  modification time changed; delete `.format_cache/` to reset it.

## Linting

| I want to …                                  | Command                                                                |
| -------------------------------------------- | ---------------------------------------------------------------------- |
| Lint the files I changed                     | `bazel run //:lint.check -- --delta`                                   |
| Lint the files I changed and apply the fixes | `bazel run //:lint -- --delta`                                         |
| Lint a package and apply the fixes           | `bazel lint --fix //<pkg>/...`                                         |
| Run only one linter, e.g. ruff               | `bazel lint --lint:aspects=//bazel/tools:aspects.bzl%ruff //<pkg>/...` |

- `--delta` lints the targets that list the changed files in their `srcs` or
  `hdrs`, plus the changed Starlark files with buildifier. It skips changed
  files no target lists and also reports findings in the unchanged files of
  those targets.
- Bazel flags go after `--delta`, e.g. `--cmk_edition=pro`: `//:lint` and
  `//:lint.check` pass them on to the `bazel lint` they run, as those given
  to `bazel run` don't reach it.
- `bazel lint` takes targets, not files: `bazel lint path/to/file.py` checks
  nothing and succeeds.
- `.aspect/cli/config.yaml` lists the linters. All of them together also
  compile C++ and Rust code and build the frontend.

## Type checking

| I want to …                                 | Command                                                  |
| ------------------------------------------- | -------------------------------------------------------- |
| Type-check a package                        | `bazel build --config=mypy //<pkg>:all`                  |
| Type-check TypeScript and Vue               | `bazel build //<pkg>:<lib>_type_check`                   |
| Type-check the frontend's Node config files | `bazel test //packages/cmk-frontend-vue:type-check-node` |

- Each `vue_library` `<lib>` has a `<lib>_type_check` target.

## Running tests

| I want to …                        | Command                                                  |
| ---------------------------------- | -------------------------------------------------------- |
| Run all unit tests                 | `bazel test //tests/unit/...`                            |
| Run the unit tests of an edition   | `bazel test --cmk_edition=pro //tests/unit/...`          |
| Run the tests of a package         | `bazel test //packages/<pkg>/...`                        |
| Run doctests                       | `bazel test --test_tag_filters=doctest //<pkg>/...`      |
| Run the frontend unit tests        | `bazel test //packages/cmk-frontend-vue:unit-test`       |
| Run the jest tests of cmk-frontend | `bazel test //packages/cmk-frontend:jest`                |
| Run the shell unit tests           | `bazel test //tests/unit-shell/agents:all`               |
| Run the agent plugin tests         | `bazel test //tests/agent-plugin-unit:agent-plugin-unit` |
| … with an old Python, e.g. 3.4     | `tests/run_tests.sh test-agent-plugin-unit-py3.4-docker` |
| Run the integration tests          | `bazel test //tests/integration/...`                     |
| Run the system tests               | `tests/run_tests.sh test-system-singlesite`              |

### Selecting tests and test output

| I want to …                       | Command                                                                                 |
| --------------------------------- | --------------------------------------------------------------------------------------- |
| Run one test file                 | `bazel test <target> --test_arg=<path/to/test_file.py>`                                 |
| Run tests by name                 | `bazel test <target> --test_filter=<expression>`                                        |
| Run one frontend test file        | `bazel test //packages/cmk-frontend-vue:unit-test --test_arg=<tests/path/file.test.ts>` |
| Run frontend tests by name        | `bazel test //packages/cmk-frontend-vue:unit-test --test_arg=-t --test_arg=<pattern>`   |
| Run one Rust test                 | `bazel test <target> --test_arg=<test name> --test_arg=--exact`                         |
| Run one C++ test                  | `bazel test <target> --test_arg=--gtest_filter=<Suite.Test>`                            |
| See the test output while it runs | `bazel test <target> --test_output=streamed`                                            |
| Rerun tests that passed before    | `bazel test <target> --cache_test_results=no`                                           |
| Hunt a flaky test                 | `bazel test <target> --runs_per_test=50`                                                |
| Read the log of the last run      | `bazel-testlogs/<pkg>/<target>/test.log`                                                |

- Test file paths are relative to the repository root for pytest and to the
  package for vitest.
- `--test_filter` becomes pytest's `-k`. A target without a matching test
  fails, so pass `--test_arg` and `--test_filter` to a single target.

### What CI runs

- Change validation of a Gerrit change runs the stages in
  `buildscripts/scripts/stages.yml`: search it for the name of a failed stage to
  see its `COMMAND`.
- The other test jobs (`buildscripts/scripts/test-*.groovy`) run targets of
  `tests/run_tests.sh` or `non-free/tests/run_tests.sh`, each a shell function
  of the same name, e.g. `test-unit()`. Running the target locally, e.g.
  `tests/run_tests.sh test-unit`, reproduces the job.

## From files to targets

```console
# The package that owns a file
$ bazel query packages/cmk-ccc/cmk/ccc/regex.py --output=package

# The test target of a test file: search its package, or //tests/unit/...
$ bazel query "kind('.*_test', rdeps(//packages/cmk-ccc/..., packages/cmk-ccc/tests/test_regex.py, 1))"

# The Python targets whose mypy results your change can affect
$ bazel query --keep_going \
    "kind('py_(library|binary|test)', rdeps(//..., set(<files>)))"
```

Files that no BUILD file mentions make the query fail; `--keep_going` still
prints the rest.

## Setup

| I want to …                             | Command                                                               |
| --------------------------------------- | --------------------------------------------------------------------- |
| Create or refresh the Python venv       | `make .venv`                                                          |
| Install `node_modules` for the IDE      | `bazel run -- @pnpm//:pnpm --dir $PWD install --frozen-lockfile`      |
| Get Bazel's tools (clangd, …) on `PATH` | `export PATH="$PATH:$(bazel run //bazel/tools:bazel_env print-path)"` |
| Generate `compile_commands.json`        | `bazel run //:refresh_compile_commands`                               |

## Dependencies

| I want to …                                              | Command                                                    |
| -------------------------------------------------------- | ---------------------------------------------------------- |
| Relock Python after editing a `*.in` file                | `bazel run //:lock_python_requirements`                    |
| Upgrade one or all Python packages                       | `python3 scripts/update_python_libs.py [--package <name>]` |
| Update `MODULE.bazel.lock` after a `MODULE.bazel` change | `bazel mod deps --lockfile_mode=update`                    |
| Update a JavaScript package                              | `bazel run -- @pnpm//:pnpm --dir $PWD update -r <package>` |

## Building and deploying

| I want to …                       | Command                                                                                 |
| --------------------------------- | --------------------------------------------------------------------------------------- |
| Build a Checkmk package           | `bazel build --cmk_version=<version> --//:disable_agent_package_signing=true //omd:deb` |
| Deploy my changes to a local site | `./scripts/cmk-dev-deploy.py`                                                           |
| Start the frontend dev server     | `bazel run //bazel/tools/devserver -- //packages/cmk-frontend-vue:vite`                 |

- `//omd:rpm` builds an RPM and requires an RPM distro, e.g.
  `--cmk_distro=almalinux-9`. The packages end up in `bazel-bin/omd/`;
  [Build settings](#build-settings) explains the flags.
- The package builds aren't hermetic yet: CI runs them in the Docker images of
  `buildscripts/infrastructure/build-nodes/`, which depend on our
  infrastructure and don't build elsewhere.

## Bazel maintenance

| I want to …                                                  | Command                                  |
| ------------------------------------------------------------ | ---------------------------------------- |
| Delete this worktree's outputs                               | `bazel clean --expunge`                  |
| Delete the outputs of deleted worktrees                      | `scripts/remove-orphaned-bazel-bases.sh` |
| Stop this worktree's Bazel server                            | `bazel shutdown`                         |
| See the applied `.bazelrc` options and failing command lines | `bazel <command> --config=debug …`       |

## Coming from other tools

| Instead of                    | Use                                                                          |
| ----------------------------- | ---------------------------------------------------------------------------- |
| `pytest path/to/test_file.py` | `bazel test <target> --test_arg=path/to/test_file.py`                        |
| `pytest -k <expression>`      | `bazel test <target> --test_filter=<expression>`                             |
| `pytest -s`                   | `bazel test <target> --test_output=streamed`                                 |
| `ruff format <files>`         | `bazel run //:format -- <files>`                                             |
| `ruff check --fix`            | `bazel lint --fix --lint:aspects=//bazel/tools:aspects.bzl%ruff //<pkg>/...` |
| `mypy`                        | `bazel build --config=mypy //<pkg>:all`                                      |
| `make format`                 | `bazel run //:format -- --delta` (`make format` formats the whole repo)      |
| `npm …` / `pnpm …`            | `bazel run -- @pnpm//:pnpm --dir $PWD …`                                     |
| `vitest …`                    | `bazel run //packages/cmk-frontend-vue:vitest -- …`                          |
| `cargo test`                  | `bazel test //packages/<crate>:all`                                          |
| `uv …`                        | `bazel run //bazel/tools:uv -- …`                                            |

## Build settings

| Flag                                 | Default        | Description                                                                                                    |
| ------------------------------------ | -------------- | -------------------------------------------------------------------------------------------------------------- |
| `--cmk_edition=<ed>`                 | `community`    | Edition: community, pro, ultimate, ultimatemt, cloud                                                           |
| `--cmk_version=<ver>`                | `UNSET`        | Version string injected into builds                                                                            |
| `--cmk_distro=<distro>`              | `ubuntu-24.04` | Target Linux distribution                                                                                      |
| `--//:disable_agent_package_signing` | `false`        | Bundle the unsigned agent package; required without our signing key                                            |
| `--//:use_faked_artifacts`           | `false`        | Replace artifacts built only in CI with placeholders and bundle the unsigned agent package; not for production |

## Configs

| Config               | What it does                                                    |
| -------------------- | --------------------------------------------------------------- |
| `--config=mypy`      | Type-checks the built Python targets with mypy (`mypy.ini`)     |
| `--config=mypy-gpl`  | Like `--config=mypy`, but with `mypy-gpl.ini`                   |
| `--config=deballast` | Reports unused dependencies of the built targets                |
| `--config=debug`     | Prints the applied `.bazelrc` options and failing command lines |
| `--config=ci`        | CI only                                                         |

`bazel/rc/<name>.rc` defines each config.

## Personal settings

For user-global settings that apply across all worktrees, use `~/.bazelrc`.
Settings for a single worktree go into `user.bazelrc` in its root, which git
ignores.

A good default to reign in bazel is

```
# --- 1. Prevent Disk/CPU priority hogging (The "Browser Savers") ---
startup --io_nice_level=7
startup --batch_cpu_scheduling

# --- 2. Cap the Server itself ---
startup --host_jvm_args=-Xmx4g

# --- 3. Existing Limits (Accumulated is fine!) ---
common --local_resources=cpu=HOST_CPUS*.5
common --local_resources=memory=HOST_RAM*.5

# --- 4. The Hidden CPU hog (Analysis Phase) ---
common --loading_phase_threads=HOST_CPUS*.5
```
