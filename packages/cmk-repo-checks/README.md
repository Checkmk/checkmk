# cmk-repo-checks

First-party checkers that enforce conventions of this repository itself.
The tools in this package analyze the repo's source and `BUILD` files rather than shipping as part of the product.

New checkers should be added as modules under `cmk/repo_checks/` with their own targets and tests under `tests/`.

## deballast

Reports over-declared Bazel `py_*` `deps` via AST-level src-vs-dep analysis.
It is implemented as a Bazel aspect (`deballast.bzl`): applied to a `py_library`/`py_binary`/`py_test` target, it runs one checker action per target that parses the target's own `srcs` for imports and flags declared deps whose direct `srcs` provide no imported module.
Results are cached per target and re-checked incrementally — only targets whose own `srcs` or whose deps' interfaces changed are re-analyzed.
It only inspects direct `srcs` of deps (not the transitive closure) and does not detect missing deps.
See the module docstring of `cmk/repo_checks/deballast.py` for the full list of heuristics and implicit-use exemptions.

### Usage

deballast is registered as a linter in `.aspect/cli/config.yaml`, so interactive use is plain `bazel lint`, which prints the findings alongside the other linters:

```console
bazel lint //cmk/gui/wato:wato
bazel lint //cmk/gui/...
```

For CI and scripted consumption, `--config=deballast` materializes the report files per analyzed target in `bazel-bin`:

```console
bazel build --config=deballast //cmk/gui/...
# quick check - human reports are empty when clean:
find bazel-bin -name "*.AspectRulesLintDeballast.out" -size +0c -exec cat {} +
# SARIF for tooling:
find bazel-bin -name "*.AspectRulesLintDeballast.report" -size +0c -exec jq -r '.runs[].results[].message.text' {} +
```

Deps confirmed unused should be removed from the corresponding `BUILD` file; verify with `bazel build`, `bazel lint`, and `bazel build --config=mypy`.

### Exemptions

A dep that is loaded at runtime (plugin discovery, fixtures) rather than imported by name is exempted per edge with a tag on the consuming target; the reason stays next to it as a comment:

```starlark
tags = ["deballast-keep=//cmk/base/modes:modes"],  # loaded at runtime via discover_commands()
```

A target whose deps are all runtime-loaded (e.g. sphinx autodoc builds) opts out entirely with `tags = ["no-deballast"]`; the generic `no-lint` tag is honored, too.
A `deballast-keep` tag that names no declared dep is reported as stale, so exemptions cannot outlive the dep they exempt.

## license-header

Checks that every `.py` file carries the correct copyright/license header for its location (GPL, Checkmk Enterprise, OMD, and the notification/alert-handler variants).
It is implemented as a Bazel aspect (`lint_license_header.bzl`) driving the per-target checker `cmk/repo_checks/license_header_checker.py`, which selects the expected header from the file path (enterprise editions, notification dirs, and specific OMD files get their own patterns) and reports mismatches.
Like the other checkers it surfaces through `bazel lint` and materializes report files under `--config=...`.

## python-extension

Flags Python source files that lack a `.py` extension, so they get picked up by formatters, linters, and type checking.
It is implemented as a Bazel aspect (`lint_python_extensions.bzl`) driving `cmk/repo_checks/python_extension_checker.py`, which parses each declared src and reports extension-less files whose content is Python.
Because it runs as an aspect over Bazel `srcs`, it only covers files that are part of a `py_*` target; a target opts out with `tags = ["no-python-extension-checker"]`.

## bazel-lint-coverage

Checks that every tracked source file is in a Bazel rule that its lint aspect visits.
The aspects above, and the language linters in `bazel/tools/aspects.bzl`, only see files declared in specific rule kinds.
A file outside those rules is never linted, and no aspect can report it.
This checker therefore works from the other side: it compares `git ls-files` with `bazel query`.

| Files                                        | Must be in                                               |
| -------------------------------------------- | -------------------------------------------------------- |
| `*.sh`, and other files with a shell shebang | `srcs` of `sh_binary`, `sh_library` or `sh_test`         |
| `*.ps1`                                      | a `filegroup` tagged `lint-with-psscriptanalyzer`        |
| `*.rs`                                       | `srcs` of `rust_binary`, `rust_library`, `rust_test`, …  |
| `*.c`, `*.cc`, `*.h`                         | `srcs` or `hdrs` of `cc_binary`, `cc_library`, `cc_test` |
| `*.js`, `*.cjs`                              | any target                                               |

A file whose extension belongs to none of the other classes counts as shell when its shebang names `sh`, `bash`, `dash` or `ksh`.
The rule kinds must match exactly. The transitioned rules from `bazel/rules/private/xcomp/`, such as `_cc_binary_transitioned`, do not count, because no aspect visits them.
A target tagged `no-lint` (or `noclippy` for Rust) does not count either.
A `filegroup` in `srcs` counts with its own `srcs`.
`bazel query` follows every `select()` branch, so the result covers all editions.
`doc/treasures/` is excluded. For C and C++ files, `agents/wnx/` (MSBuild) is excluded as well.
Files with the attribute `rules-lint-ignored=true` in a `.gitattributes` file are excluded, for example vendored files that are kept identical to upstream.
For Rust, build scripts (`build.rs`) and the `packages/*/src/version.rs` files are excluded.
Clippy never lints build scripts, whether Cargo or `cargo_build_script` runs them.
The `version.rs` files exist only for Cargo, because Bazel sets the version with a build flag.

For C and C++, the check guarantees less than for the other classes.
A source file in `cc_test` and a header in `hdrs` count as covered, but clang-tidy lints neither of them today.
The `clang_tidy` aspect in `bazel/tools/aspects.bzl` uses the default rule kinds of `aspect_rules_lint` (`cc_binary`, `cc_library`) and an empty `header_filter`.
The check still keeps these files in a `cc_*` target, so a later change of the aspect configuration (CMK-40386) covers all of them at once.

Files that were uncovered when the check was introduced are listed in `bazel_lint_coverage_known_offenders.txt`.
The list may only shrink. The check fails on an uncovered file that is not listed, and on a listed file that is covered by now or no longer exists.

### Usage

The checker runs `bazel query` itself, so start it with `bazel run`:

```console
bazel run //packages/cmk-repo-checks:bazel_lint_coverage
# all current offenders, in the format of the known-offenders file:
bazel run //packages/cmk-repo-checks:bazel_lint_coverage -- --print-offenders
```

The "Bazel sanity check" stage of the change validation runs it on every change.
Exit code 1 means new or stale offenders, exit code 2 means that a `bazel query` failed or returned no files.

To fix a new offender, add the file to a matching target, for example an `sh_library` next to the script, and check it with `bazel lint` on that target.
To fix a listed offender, do the same and remove its line from the list in the same commit.

## Development

```console
# Run the tests
bazel test //packages/cmk-repo-checks:test

# Format, lint, type-check
bazel run //:format packages/cmk-repo-checks
bazel lint //packages/cmk-repo-checks:all
bazel build --config=mypy //packages/cmk-repo-checks:all
```
