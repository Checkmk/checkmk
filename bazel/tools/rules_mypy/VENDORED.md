# Vendored rules_mypy

This is [rules_mypy](https://github.com/bazel-contrib/rules_mypy) v0.41.0, taken
from the release archive
<https://github.com/theoremlp/rules_mypy/releases/download/v0.41.0/rules_mypy-0.41.0.tar.gz>
(its former home, as the Bazel Central Registry has it; sha256
`5212d414f744f798a6c2bd73d499ef6c89a5d3cb7caf1c90970fe32a5bb61f66`) and
licensed under the Apache License 2.0, see [LICENSE](LICENSE). Upstream has
had no release since 2026-03-31, while we needed seven patches on top of it, so
we keep our own copy. [readme.md](readme.md) is upstream's documentation: read
`@rules_mypy//mypy` there as `//bazel/tools/rules_mypy/mypy`.

The layout and file names are upstream's. Keep it that way, and list every
change here.

## Left out

`MODULE.bazel`, `WORKSPACE.bazel`, the top-level `BUILD.bazel`, `.bazelrc`,
`.bazelversion`, `.bazelignore`, `.bcr/`, `.github/`, `.vscode/`,
`.gitattributes`, `.gitignore` and `mypy/private/requirements.{in,txt}` with the
`pip_compile` and `create_venv` targets. They set up rules_mypy as a repository
and module of its own.

## Porting

- Labels `//mypy/…` and `@rules_mypy//mypy/…` are
  `//bazel/tools/rules_mypy/mypy/…`. The BUILD file that
  `mypy/private/types.bzl` generates loads
  `@@//bazel/tools/rules_mypy/mypy:py_type_library.bzl`.
- mypy comes from `@mypy_requirements` (`bazel/tools/mypy-requirements.txt`) and
  click from `@cmk_requirements`, not from upstream's `@rules_mypy_pip`. No
  `requirements.in` lists click, it comes with flask and others. Should it ever
  drop out of the lock, add it to `tests/dev-requirements.in`.
  `@mypy_requirements` leaves typing-extensions out, so the `mypy_cli` macro
  adds it from `@cmk_requirements`.
- The `mypy_cli` macro and `:py_type_library` in `mypy/private/BUILD.bazel` use
  our default Python version, the only one our pip hubs have, instead of 3.12.
- Each changed file starts with a comment pointing here.

## Fixes and additions

In `mypy/private/mypy.bzl`:

- Stub directories go into `MYPYPATH` only for import roots that hold stubs,
  after the source directories and before the generated ones, each before its
  ancestors (upstream PR #146).
- `_types_keys` and `_types_values` use `cfg = "exec"`. Otherwise, analysing
  targets for other platforms (e.g. musl-aarch64) fails on pip aliases.
- `MYPYPATH` always contains `bin_dir`, not only when a dependency brings
  generated files, so that generated modules are found (e.g. `cmc_proto`).
- `mypy_cli` takes `pyc_collection`, to ship mypy's bytecode.

In `mypy/private/mypy_runner.py`:

- mypy runs with `--show-column-numbers`, which
  `buildscripts/scripts/collect_type_errors.py` uses.
- Upstream caches are merged with hardlinks instead of copies (like upstream PR
  #137).
- mypy runs with `--no-sqlite-cache` when it keeps a cache directory (upstream
  PR #145).
- The docstring of `_hardlink_tree` notes why it probably copies locally.

Both cache fixes only matter with `cache = True`, which
`bazel/tools/aspects.bzl` currently turns off.

## Limits of the cache merge

Two things probably keep the merge from saving much, so check them before
turning `cache = True` on again:

- `bazel/rc/performance.rc` puts the sandboxes on `/dev/shm`, while the
  upstream caches stay in `bazel-out` on disk. `os.link` fails across
  filesystems, so the runner copies. Only CI resets `--sandbox_base`, in
  `bazel/rc/ci.rc`.
- mypy records the path under which it found a module in the module's meta
  file (`.meta.ff`), and rewrites that file when the path changes. Checked
  sources get paths like `cmk/foo.py`, imports found via `MYPYPATH`, which
  starts with `.`, get `./cmk/foo.py`, and typeshed's stubs get absolute paths
  in the runfiles of `mypy_cli`, which differ per sandbox. So probably every
  action rewrites the meta files of typeshed's modules and of the modules that
  an upstream action checked itself. Only the data files (`.data.ff`) would
  stay shared. mypy's `--bazel` option skips that comparison and may help.

## Bazel versions

Keep upstream's compatibility code, e.g. `PyInfo` via `bazel_features` (native
in Bazel 8, gone in Bazel 9). Upstream's CI only covers Bazel 7 and 8, so
switching to Bazel 9 needs a check of this copy, too.

## Module extension

The `types` extension (`mypy/types.bzl`) is part of the main repository now, so
any change to it or to the files it loads, even to a comment, changes its digest
in `MODULE.bazel.lock`. Update the lockfile in the same commit with
`bazel mod deps --lockfile_mode=update`.

## Checks

Our usual linters, formatters and mypy cover this directory, so the code follows
them: import order, `X | None`, `Iterator[str]`, `contextlib.suppress`, sorted
attribute dictionaries and a few renamed variables. Only the license header
checks, `license_header_checker.py` and `.pre-commit-scripts/check-licence`,
skip the two Python files, which stay under the Apache License. The pre-commit
hook `trailing-whitespace` skips `readme.md`, to keep upstream's Markdown line
break.

## Switching back to upstream

Add `bazel_dep(name = "rules_mypy", …)`, load from `@rules_mypy//mypy` in
`bazel/module/py.MODULE.bazel`, `bazel/tools/aspects.bzl` and
`bazel/tools/BUILD`, and delete this directory and its entries in
`license_header_checker.py`, `.pre-commit-scripts/check-licence` and
`.pre-commit-config.yaml`. Drop the `bazel_features` dependency from
`MODULE.bazel` if nothing else uses it, and update `MODULE.bazel.lock`. Put
`tags = ["no-mypy"]` back on `//bazel/tools:mypy_cli_original`: upstream's
`mypy_runner.py` doesn't pass our mypy settings. Keep its `mypy_requirement` and
`python_version`, since upstream defaults to Python 3.12 and its own pip hub,
and point the comment on `types` in `bazel/tools/aspects.bzl` back at upstream.
Move the notes in "Limits of the cache merge" into the comment on `cache`
there.
Fixes that upstream hasn't merged go into patches for a
`single_version_override`: diff this directory against the release archive and
leave out the porting changes and those for our tooling.
