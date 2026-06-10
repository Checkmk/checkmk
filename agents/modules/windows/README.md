# Windows agent Python module (`python-3.cab`)

The Windows agent ships a self-contained CPython runtime + a Pipfile worth
of Python packages, bundled as `python-3.cab`. The MSI installer drops it
under `C:\ProgramData\checkmk\agent\modules\python-3`, and the agent runs
`postinstall.cmd` to verify the directories on the target host.

## Build

The cab is built on Linux, driven by Bazel:

```bash
bazel build //agents/modules/windows:python_3_cab
ls   bazel-bin/agents/modules/windows/python_3_cab.cab
```

The CI entry point is `buildscripts/scripts/winagt-build-modules.groovy`,
which runs on a Linux build node and pushes the resulting cab to
`agents/modules/windows/artefacts/python-3.cab`.

Build prerequisites on the Linux node: only `bazel` itself plus the
standard toolchain bazel modules need (a C compiler for the foreign-cc
builds of `msitools` / `cabextract`). Everything else is hermetic via
bazel modules:

- `msiinfo` (from `@msitools`) — reads MSI tables and extracts cabinet
  streams.
- `cabextract` (from `@cabextract`) — unpacks the python.org cabinet
  streams; LZX-compressed, which the pure-Python `cabarchive` can't
  read.
- `cabarchive` (Python, vendored via `@cabarchive`) — writes the final
  `python-3.cab` (MSZIP-compressed, fixed timestamps; bit-identical
  given the same inputs).
- the sha256-pinned `pip` wheel from `@windows_python_wheels`, run under
  the repo's hermetic CPython (`pip_offline.py`) — resolves Windows
  wheels offline via `--no-index --find-links` with
  `--platform win_amd64 --only-binary=:all:`. Nothing Windows runs
  during the build, and the build action needs no network.

## Pinning

- CPython version: `PYTHON_VERSION_WINDOWS` in `defines.make` (also baked
  into `BUILD.bazel`'s `python_version`).
- Per-feature MSIs (`ucrt`, `core`, `exe`, `lib`, `pip`): SHA256-pinned
  `http_file` entries in `MODULE.bazel`.
- Python packages: `pipfiles/3/Pipfile` is the human source of truth (plus
  the pip seed pin in `refresh_wheel_pins.py`); the resolved win_amd64
  closure is pinned in `windows_python_wheels.lock.json`, from which the
  fetch-phase repo also generates the `REQUIREMENTS` list `BUILD.bazel`
  installs — request and closure can't diverge.

To refresh after a CPython version bump:

```bash
python3 agents/modules/windows/refresh_msi_pins.py 3.13.13
bazel run //agents/modules/windows:refresh_wheel_pins -- 3.13.13
```

Paste the printed `http_file(...)` blocks over the matching ones in
`MODULE.bazel`, update `python_version` in `BUILD.bazel` and
`PYTHON_VERSION_WINDOWS` in `defines.make`.

## Layout produced

```
python-3.cab
|-- postinstall.cmd          # verbatim from agents/modules/windows/postinstall.cmd
|-- python.exe               # base interpreter (from core.msi + exe.msi)
|-- python313.dll
|-- DLLs/
|-- Lib/                     # stdlib (from lib.msi); strip list mirrors clean_environment.cmd history
|-- Lib/site-packages/pip/   # the pinned pip wheel (replaces the ensurepip bootstrap)
+-- .venv/
    |-- pyvenv.cfg           # 3-liner; home points at C:\ProgramData\checkmk\agent\modules\python-3
    |-- Scripts/             # interpreter + runtime DLL copies, stdlib .pyd mirror,
    |                        # venv launchers, console-script .exe wrappers (pip,
    |                        # chardetect, ...), activation scripts, UCRT redistributables
    +-- Lib/site-packages/   # Pipfile packages + pip, installed cross-platform from Linux
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
- **MSZIP instead of LZX:18** (~20% larger cab; no Linux tool writes LZX,
  `expand.exe` reads both) and fixed member timestamps (reproducible
  output).
- **Dropped dead weight**: the pipenv/virtualenv toolchain that leaked
  into the base `Lib/site-packages`, virtualenv bookkeeping files, and
  `.venv/Scripts` members with no MSI source and no function
  (`py.exe`/`pyw.exe`/`pyshellext.dll`, `_tkinter.pyd`, `xxlimited*.pyd`,
  `zlib1.dll`).

## Why not Wine

Earlier proofs of concept (`~/Projects/personal/windows/experiments/
python_cab_pipenv/`) used `wine msiexec /a` for MSI extraction and a
Wine-side `pip` for package installation. Both are removable:

- MSIs are zip-of-cab containers with a structured stream catalog;
  `msiextract` walks the File/Directory tables natively on Linux.
- Linux `pip install --platform win_amd64 --only-binary=:all:` resolves
  Windows wheels without executing them. Every Pipfile dependency
  (incl. `cryptography`, `pywin32`, `pyyaml`) ships a `cp313-win_amd64`
  wheel.

The post-install scripts that `pywin32` and friends ship are _not_ run by
this build, and the historical Windows-side build did not run them
either — the agent invokes them on the target host after CAB extraction.

## Tests

`tests/` contains the integration test suite that exercises the produced
CAB on a Windows host. It is invoked separately from the build:

```bash
make -C agents/modules/windows/tests test-integration
```
