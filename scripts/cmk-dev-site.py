#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Launcher for the cmk-dev-site commands: runs them from this checkout's
sources on the checkout's own venv.

This file and its symlinks next to it carry the names of the commands the
cmk-dev-site wheel installs; the name it is started under picks the command.
The name must survive the re-exec onto the venv interpreter, so the second
pass is started with the path the caller used, not the resolved file.

The working directory is left alone: cmk-dev-install takes paths relative to
the caller's directory.
"""

import importlib
import os
import sys
from pathlib import Path

_COMMANDS = {
    "cmk-dev-site": ("cmk_dev_site.cmk_dev_site", "main"),
    "cmk-dev-install": ("cmk_dev_site.cmk_dev_install", "main"),
    "cmk-dev-install-site": ("cmk_dev_site.cmk_dev_install_site", "main"),
    "cmk-dev-site-mock-auth": ("cmk_dev_site.saas.oidc_service", "run"),
}

# The package uses 3.14-only syntax (PEP 758 except clauses without
# parentheses), so an older venv would fail with a SyntaxError instead of
# the message below.
_MIN_PYTHON = (3, 14)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_VENV_PYTHON = _REPO_ROOT / ".venv" / "bin" / "python3"
_STARTED_AS = Path(sys.argv[0]).absolute()
_COMMAND = _STARTED_AS.name.removesuffix(".py")

if _COMMAND not in _COMMANDS:
    sys.stderr.write(
        f"{_STARTED_AS.name}: unknown command name. Start one of: "
        f"{', '.join(f'scripts/{name}.py' for name in _COMMANDS)}\n"
    )
    sys.exit(1)

# CMK_DEV_SITE_REEXEC marks the second pass, which runs on the venv interpreter.
if "CMK_DEV_SITE_REEXEC" not in os.environ:
    if not _VENV_PYTHON.is_file():
        sys.stderr.write(
            f"{_COMMAND}: {_VENV_PYTHON} not found.\nRun 'make .venv' in {_REPO_ROOT} to create it.\n"
        )
        sys.exit(1)
    os.environ["CMK_DEV_SITE_REEXEC"] = "1"
    os.execv(str(_VENV_PYTHON), [str(_VENV_PYTHON), str(_STARTED_AS), *sys.argv[1:]])

if sys.version_info < _MIN_PYTHON:
    sys.stderr.write(
        f"{_COMMAND} needs Python >= {'.'.join(map(str, _MIN_PYTHON))}, "
        f"but the repo venv runs Python {sys.version.split()[0]}.\n"
        f"Rebuild it: make .venv\n"
    )
    sys.exit(1)

sys.path.insert(0, str(_REPO_ROOT / "packages" / "cmk-dev"))

if __name__ == "__main__":
    _module, _function = _COMMANDS[_COMMAND]
    sys.exit(getattr(importlib.import_module(_module), _function)())
