#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Library for pylint checks of Checkmk

import os
from pathlib import Path

from pylint.lint import PyLinter  # type: ignore[import]

from tests.testlib import is_enterprise_repo


def is_python_file(path: Path, shebang_name: str | None = None) -> bool:
    if shebang_name is None:
        shebang_name = "python3"
    if not os.path.isfile(path) or os.path.islink(path):
        return False
    with path.open() as f:
        shebang = f.readline().rstrip()
    return shebang.startswith("#!") and shebang.endswith(shebang_name)


# Is called by pylint to load this plugin
def register(linter: PyLinter) -> None:
    # Disable some CEE/CME/CPE specific things when linting CRE repos
    if not is_enterprise_repo():
        # Is used to disable import-error. Would be nice if no-name-in-module could be
        # disabled using this, but this does not seem to be possible :(
        linter.global_set_option(
            "ignored-modules",
            "cmk.base.cee,cmk.gui.cee,cmk.gui.cme,cmk.gui.cme.managed,cmk.base.cpe,cmk.gui.cpe",
        )
        # This disables no-member errors
        linter.global_set_option(
            "generated-members",
            r"(cmk\.base\.cee|cmk\.gui\.cee|cmk\.gui\.cme|cmk\.base\.cpe|cmk\.gui\.cpe)(\..*)?",
        )
