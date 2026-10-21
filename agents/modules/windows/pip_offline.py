#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Install Windows wheels with the pinned pip, offline.

The python-3.cab build installs Windows wheels with a Linux pip.  Driving pip
through this ``py_binary`` (instead of ``python3 -m pip`` from the host's PATH)
pins the interpreter to the repo's hermetic CPython toolchain, so the metadata
pip writes (e.g. ``RECORD`` bytecode entries like ``cpython-313``) matches the
CAB's Python version instead of whatever the build host ships.

The pip *code* comes from the sha256-pinned ``pip-*.whl`` in the wheel closure
(a wheel is importable straight off ``sys.path``, exactly like ``get-pip.py``
does it), so the hermetic runtime doesn't need pip installed at all and the
resolving pip version is pinned, too.

Every install is the same one: win_amd64 binary wheels for the given CPython,
resolved from the wheel dir alone (``--no-index --find-links``) into
``--target``.

Usage::

    pip_offline.py --wheel-dir DIR --python-version 3.14.7 --target DIR
        [--no-compile] REQUIREMENT...
"""

from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path


def _pip_wheel(wheel_dir: Path) -> Path:
    candidates = sorted(wheel_dir.glob("pip-*.whl"))
    if not candidates:
        sys.exit(f"error: no pip-*.whl in {wheel_dir}")
    return candidates[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel-dir", required=True, type=Path, help="the --find-links dir")
    parser.add_argument("--python-version", required=True, help="CPython version, e.g. 3.14.7")
    parser.add_argument("--target", required=True, help="dir to install into")
    parser.add_argument("--no-compile", action="store_true", help="write no bytecode")
    parser.add_argument("requirement", nargs="+", help="name==version to install")
    args = parser.parse_args()

    major, minor = args.python_version.split(".")[:2]
    sys.path.insert(0, str(_pip_wheel(args.wheel_dir)))
    sys.argv = [
        "pip",
        "install",
        "--no-index",
        "--find-links",
        str(args.wheel_dir),
        "--platform",
        "win_amd64",
        "--python-version",
        f"{major}.{minor}",
        "--implementation",
        "cp",
        "--abi",
        f"cp{major}{minor}",
        "--only-binary=:all:",
        "--no-warn-script-location",
        *(["--no-compile"] if args.no_compile else []),
        "--target",
        args.target,
        *args.requirement,
    ]
    runpy.run_module("pip", run_name="__main__", alter_sys=True)


if __name__ == "__main__":
    main()
