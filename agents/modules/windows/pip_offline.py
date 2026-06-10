#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Run the pinned pip CLI from its own wheel, offline.

The python-3.cab build installs Windows wheels with a Linux pip.  Driving pip
through this ``py_binary`` (instead of ``python3 -m pip`` from the host's PATH)
pins the interpreter to the repo's hermetic CPython toolchain, so the metadata
pip writes (e.g. ``RECORD`` bytecode entries like ``cpython-313``) matches the
CAB's Python version instead of whatever the build host ships.

The pip *code* comes from the sha256-pinned ``pip-*.whl`` in the wheel closure
(a wheel is importable straight off ``sys.path``, exactly like ``get-pip.py``
does it), so the hermetic runtime doesn't need pip installed at all and the
resolving pip version is pinned, too.

Usage::

    pip_offline.py <pip-wheel-or-find-links-dir> <pip args...>
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def _pip_wheel(path: Path) -> Path:
    if path.is_dir():
        candidates = sorted(path.glob("pip-*.whl"))
        if not candidates:
            sys.exit(f"error: no pip-*.whl in {path}")
        return candidates[0]
    return path


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    wheel = _pip_wheel(Path(sys.argv[1]))
    sys.path.insert(0, str(wheel))
    sys.argv = ["pip", *sys.argv[2:]]
    runpy.run_module("pip", run_name="__main__", alter_sys=True)


if __name__ == "__main__":
    main()
