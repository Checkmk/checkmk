#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Launcher for cmk-dev-deploy: runs the tool from this checkout's sources on
the checkout's own venv.

Deliberately not a ``bazel run`` target: launching via Bazel would queue
behind any running Bazel command in the checkout, and its build phase runs
with the default edition while the tool pins the site edition on its own
Bazel calls -- every launch would flip the server configuration and discard
the analysis cache.

Always the repo venv, never whatever python3 is first on $PATH: two
interpreters that both satisfy the minimum version can still disagree in
subtle ways, and the venv is the one every contributor gets from
``make .venv``.  The interpreter the shebang picks only runs the re-exec
below, so this module must stay parseable by old Pythons.
"""

import os
import sys
from pathlib import Path

# The package uses 3.14-only syntax (e.g. PEP 758 except tuples without
# parentheses), so an older venv would fail with a SyntaxError deep inside
# the package instead of a message that says what's actually wrong.
_MIN_PYTHON = (3, 14)

# The launcher always runs the checkout it lives in, independent of the
# caller's working directory (matching the old `bazel run` semantics).
_REPO_ROOT = Path(__file__).resolve().parent.parent
_VENV_PYTHON = _REPO_ROOT / ".venv" / "bin" / "python3"

# CDD_REEXEC marks the second pass, which runs on the venv interpreter.
if "CDD_REEXEC" not in os.environ:
    if not _VENV_PYTHON.is_file():
        sys.stderr.write(
            f"cmk-dev-deploy: {_VENV_PYTHON} not found.\n"
            f"Run 'make .venv' in {_REPO_ROOT} to create it.\n"
        )
        sys.exit(1)
    os.environ["CDD_REEXEC"] = "1"
    os.execv(str(_VENV_PYTHON), [str(_VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])

if sys.version_info < _MIN_PYTHON:
    sys.stderr.write(
        f"cmk-dev-deploy needs Python >= {'.'.join(map(str, _MIN_PYTHON))}, "
        f"but the repo venv runs Python {sys.version.split()[0]}.\n"
        f"Rebuild it: make .venv\n"
    )
    sys.exit(1)

os.chdir(_REPO_ROOT)
sys.path.insert(0, str(_REPO_ROOT / "packages" / "cmk-dev-deploy"))

# Must come after the version guard: package modules use syntax that older
# interpreters cannot even parse.
from cmk.dev_deploy.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
