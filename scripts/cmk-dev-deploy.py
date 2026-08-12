#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Launcher for cmk-dev-deploy: runs the tool from this checkout's sources.

Deliberately not a ``bazel run`` target: launching via Bazel would queue
behind any running Bazel command in the checkout, and its build phase runs
with the default edition while the tool pins the site edition on its own
Bazel calls -- every launch would flip the server configuration and discard
the analysis cache.  The tool is stdlib-only, so running the sources
directly needs nothing but a recent Python.
"""

import os
import sys
from pathlib import Path

# The package uses 3.14-only syntax (e.g. PEP 758 except tuples without
# parentheses), so older interpreters fail with a SyntaxError at import.
_MIN_PYTHON = (3, 14)

# The launcher always runs the checkout it lives in, independent of the
# caller's working directory (matching the old `bazel run` semantics).
_REPO_ROOT = Path(__file__).resolve().parent.parent

if sys.version_info < _MIN_PYTHON:
    # System interpreters are usually older; fall back to the repo venv.
    # CDD_REEXEC guards against a loop when the venv Python is old too.
    venv_python = _REPO_ROOT / ".venv" / "bin" / "python3"
    if venv_python.is_file() and "CDD_REEXEC" not in os.environ:
        os.environ["CDD_REEXEC"] = "1"
        os.execv(str(venv_python), [str(venv_python), str(Path(__file__).resolve()), *sys.argv[1:]])
    sys.stderr.write(
        f"cmk-dev-deploy needs Python >= {'.'.join(map(str, _MIN_PYTHON))}, "
        f"but this is Python {sys.version.split()[0]}.\n"
        f"Create or update the repo virtualenv (make .venv) -- the launcher uses\n"
        f"{venv_python} automatically when the system Python is too old.\n"
    )
    sys.exit(1)

os.chdir(_REPO_ROOT)
sys.path.insert(0, str(_REPO_ROOT / "packages" / "cmk-dev-deploy"))

# Must come after the version guard: package modules use syntax that older
# interpreters cannot even parse.
from cmk.dev_deploy.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
