# Windows agent Python module (`python-3.cab`)

The Windows agent ships a self-contained CPython runtime + a pinned set
of Python packages, bundled as `python-3.cab`. The MSI installer drops it
under `C:\ProgramData\checkmk\agent\modules\python-3`, and the agent runs
`postinstall.cmd` to verify the directories on the target host.

## Build

The cab is built on Linux, driven by Bazel:

```bash
bazel build //agents/modules/windows:python_3_cab
ls   bazel-bin/agents/modules/windows/python_3_cab.cab
```

The CI entry point is `buildscripts/scripts/winagt-build-modules-linux.groovy`,
which runs on a Linux build node and pushes the resulting cab to
`agents/modules/windows/artefacts/python-3.cab`.

Build prerequisites on the Linux node: only `bazel` itself plus a C
compiler for the foreign-cc builds of `msitools` / `cabextract`.
Everything else is hermetic via bazel modules:

- `msiinfo` (from `@msitools`) — reads MSI tables and extracts cabinet
  streams.
- `cabextract` (from `@cabextract`) — unpacks the python.org cabinet
  streams; LZX-compressed, which the pure-Python `cabarchive` can't
  read.
- `cabarchive` (Python, vendored via `@cabarchive`) — writes the final
  `python-3.cab` (MSZIP-compressed, fixed timestamps; bit-identical
  given the same inputs).
- the pinned `pip` wheel from the `@windows_python_wheels` hub, run
  under the hermetic CPython of the CAB's `major.minor` line
  (`pip_offline.py`, pinned via its `py_binary`'s `python_version`) —
  installs the Windows wheels offline (`--no-index --find-links`,
  `--platform win_amd64 --only-binary=:all:`). Nothing Windows runs
  during the build, and the build action needs no network.

## Pinning

- CPython version: `PYTHON_VERSION_WINDOWS` in `package_versions.bzl`, the
  single source of truth for the CAB's CPython version: `defines.make`
  `sed`-reads it out of there at make time, `BUILD.bazel` `load()`s it into
  `python_version`, and the MSI URLs below derive from it. Only
  `MODULE.bazel` files duplicate the version — they cannot `load()` it; see
  the bump procedure below.
- Per-feature MSIs (`ucrt`, `core`, `exe`, `lib`, `pip`): declared by the
  `//bazel/extensions:python_cab_repositories.bzl` module extension (wired up by
  `bazel/module/python_cab.MODULE.bazel`), which builds the download URLs from
  `PYTHON_VERSION_WINDOWS` — a `.bzl` file can `load()` it, whereas
  `MODULE.bazel` cannot, so the version is not spelled out twice. Only the
  SHA256 hashes (`_MSI_SHA256`) are maintained by hand.
- Python packages: edit `requirements-windows.in`, then regenerate the
  sha256-pinned `requirements-windows.txt` with
  `bazel run //agents/modules/windows:requirements_windows` (same uv flow
  as the repo's other requirements files, but resolved under the hermetic
  interpreter of `PYTHON_VERSION_WINDOWS`'s `major.minor` line — rules_uv's
  `py3_runtime` — so the lock tracks the CAB's Python, independent of the
  site toolchain). The `@windows_python_wheels` pip.parse hub
  (`bazel/module/python_cab.MODULE.bazel`) downloads the pinned wheels; stale pins
  fail `:requirements_windows_test` in CI
  (`make check_python_requirements`).

  Keep `requirements-windows.in` unpinned — the resolved
  `requirements-windows.txt` is the pin. Version bounds go into
  `constraints-windows.txt`, which the resolution consumes via
  `:requirements-windows-in`. That file is deliberately separate from
  `//:constraints.txt`: the CAB resolves for `win_amd64` with
  `--only-binary=:all:`, so a bound that is satisfiable for the site can be
  unsatisfiable here, and a shared file would let a server-side hold break
  the agent build (and vice versa). Every entry needs a `CMK-<id>` ticket for
  its removal, enforced by
  `//tests/code_quality/requirements:requirements_files`.

  `requirements-windows.txt` is also a `manifest_srcs` entry of
  `//omd/dependency_management:list_of_dependencies`. The SBOM aspect already
  finds the CAB's packages in the build graph, through the `package_metadata`
  of the hub's generated whl repositories, but it carries no artifact hashes
  for them -- the manifest entry is what fills in their SHA256 hashes and a
  `path` property naming this file. Without it, the packages whose only source
  is the CAB (`chardet`, `colorama`, `pip`, `pysocks`, `pywin32`, `urllib3`)
  reach the bill of materials with an empty `hashes` list.

  Because the aspect sees them from the hub alone, a package is in the bill of
  materials from the moment the hub exists, so adding one also needs a license
  in `automatically_researched_licenses.json` (via
  `bazel run //omd/dependency_management:research_licenses`) or
  `manually_researched_licenses.json`, else
  `//omd/dependency_management:test_licenses` fails.

## Bumping the Python version

`PYTHON_VERSION_WINDOWS` tracks the CAB's Python independently of the site
toolchain (`PYTHON_VERSION`); everything a `BUILD`/`.bzl` file can `load()`
derives from it. `MODULE.bazel` files cannot `load()`, so a few literals
live there and are cross-checked against `PYTHON_VERSION_WINDOWS` by
`//tests/code_quality/requirements:requirements_files` — that test's failure
message is the authoritative checklist if this section and reality ever
disagree.

For a **patch bump** (same `major.minor`, e.g. 3.13.14 → 3.13.15):

- bump `PYTHON_VERSION_WINDOWS` in `package_versions.bzl` — the MSI URLs
  follow automatically,
- then regenerate the hashes and the wheel closure:

  ```bash
  bazel run //agents/modules/windows:refresh_msi_pins
  bazel run //agents/modules/windows:requirements_windows
  ```

  `refresh_msi_pins` takes no version: the `py_binary` passes
  `PYTHON_VERSION_WINDOWS` through `args`, so it cannot fetch hashes for a
  different version than the extension requests.

- paste the printed `_MSI_SHA256` map over the one in
  `bazel/extensions/python_cab_repositories.bzl`,
- upload the five MSIs to the upstream mirror as
  `python-<version>-amd64-<feature>.msi` — the fallback URL is built from
  `PYTHON_VERSION_WINDOWS`, but nothing populates the mirror automatically, so
  until they are uploaded the fallback 404s and only python.org serves them,
- optionally bump the `x86_64-pc-windows-msvc`
  `single_version_platform_override` (version + url + sha256) in
  `bazel/module/py.MODULE.bazel` — python-build-standalone releases can lag
  python.org, and a patch-level drift between the build-time toolchain and
  the shipped MSIs is harmless.

For a **minor bump** (e.g. 3.13.x → 3.14.x), additionally:

- update `pip.parse(python_version = ...)` for the `windows_python_wheels`
  hub in `bazel/module/python_cab.MODULE.bazel`,
- in `bazel/module/py.MODULE.bazel`: update the `x86_64-pc-windows-msvc`
  `single_version_platform_override` to the new minor (and add an
  `x86_64-unknown-linux-gnu` one for it, so the resolver runtime is pinned
  too), and update the `use_repo(python, "python_<X_Y>_x86_64-unknown-linux-gnu")`
  repo name,
- while the minor differs from the site toolchain's, also register it:
  `python.toolchain(python_version = "3.YY")` — and drop that registration
  again once the two re-converge; rules_python rejects a duplicate
  registration of the same version from one module. A minor unknown to the
  pinned rules_python release needs a rules_python bump first.

A stale literal fails at analysis time anyway (the hub's aliases and the
toolchain resolution hard-fail on a version mismatch), but the code-quality
test is the curated diagnostic that names every spot.

## Layout produced

```
python-3.cab
|-- postinstall.cmd          # verbatim from agents/modules/windows/postinstall.cmd
|-- python.exe               # base interpreter (from core.msi + exe.msi)
|-- python3XX.dll            # XX = PYTHON_VERSION_WINDOWS's minor
|-- DLLs/
|-- Lib/                     # stdlib (from lib.msi); strip list mirrors clean_environment.cmd history
|-- Lib/site-packages/pip/   # the pinned pip wheel (replaces the ensurepip bootstrap)
+-- .venv/
    |-- pyvenv.cfg           # 3-liner; home points at C:\ProgramData\checkmk\agent\modules\python-3
    |-- Scripts/             # interpreter + runtime DLL copies, stdlib .pyd mirror,
    |                        # venv launchers, console-script .exe wrappers (pip,
    |                        # chardetect, ...), activation scripts, UCRT redistributables
    +-- Lib/site-packages/   # pinned packages + pip, installed cross-platform from Linux
```

## Fidelity vs the historic Windows-built CAB

The Linux build reproduces the historic CAB's layout file-for-file, with
these deliberate differences:

- **Official binaries.** All PE files come from the python.org MSIs:
  Authenticode-signed and PGO-built, where the old flow compiled CPython
  from source unsigned. Stdlib `.py` files keep the MSIs' CRLF endings
  (the source tarball had LF).
- **Working wrapper/activation scripts.** The old build baked the _build
  machine's_ path (`D:\w\workspace\...`) into the `.exe` wrappers' shebangs
  and the activate scripts; we bake the production install path.
- **One extra wrapper.** `.venv/Scripts/cffi-gen-src.exe` — cffi grew the
  console entry point after the historic lock; a native Windows pip
  install of the current closure would ship it.
- **MSZIP instead of LZX:18** (~20% larger cab; no Linux tool writes LZX,
  `expand.exe` reads both) and fixed member timestamps (reproducible
  output).
- **Dropped dead weight**: the pipenv/virtualenv toolchain that leaked
  into the base `Lib/site-packages`, virtualenv bookkeeping files, and
  `.venv/Scripts` members with no MSI source and no function
  (`py.exe`/`pyw.exe`/`pyshellext.dll`, `_tkinter.pyd`, `xxlimited*.pyd`,
  `zlib1.dll`).

## Why not Wine

Earlier proofs of concept used `wine msiexec /a` for MSI extraction and a
Wine-side `pip` for package installation. Both are removable:

- MSIs are zip-of-cab containers with a structured stream catalog;
  `msiextract` walks the File/Directory tables natively on Linux.
- Wheels are zip archives, so installing one is unpacking it plus writing
  metadata — no Windows interpreter needed. `uv` resolves the closure for
  `x86_64-pc-windows-msvc` with `--only-binary=:all:`, so every pin is a
  `win_amd64` or pure-Python wheel and never an sdist that would want a
  compiler; `pip_offline.py` then installs those wheels on Linux with
  `--no-index --find-links`.

The post-install scripts that `pywin32` and friends ship are _not_ run by
this build, and the historical Windows-side build did not run them
either — the agent invokes them on the target host after CAB extraction.

## Tests

`tests/` contains the integration test suite that exercises the produced
CAB on a Windows host. It is invoked separately from the build:

```bash
make -C agents/modules/windows/tests test-integration
```
