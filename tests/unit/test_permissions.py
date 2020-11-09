#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path
from typing import Callable, List, Tuple

from testlib import cmk_path


def is_executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def is_not_executable(path: Path) -> bool:
    return path.is_file() and not os.access(path, os.X_OK)


_GLOBAL_EXCLUDES = [
    ".gitignore",
    ".f12",
]

_PERMISSIONS: List[Tuple[str, Callable[[Path], bool], List[str]]] = [
    # globbing pattern                check function,   excludes
    ('active_checks/*', is_executable, ['Makefile', 'check_mkevents.cc']),
    ('agents/special/agent_*', is_executable, []),
    ('agents/special/lib/*', is_not_executable, []),
    ('agents/check_mk_agent.*', is_executable, ['check_mk_agent.spec']),
    ('agents/plugins/*', is_executable,
     ['README', 'mk_filestats.pyc', 'mk_jolokia.pyc', 'mk_docker.pyc', "Makefile"]),
    ('checks/*', is_not_executable, []),
    ('checkman/*', is_not_executable, []),
    ('inventory/*', is_not_executable, []),
    ('pnp-templates/*', is_not_executable, []),
    ('notifications/*', is_executable, ['README', 'debug']),
    ('bin/*', is_executable, ['Makefile', 'mkevent.cc', 'mkeventd_open514.cc']),
    # Enterprise specific
    ('enterprise/bin/*', is_executable, []),
    ('enterprise/active_checks/*', is_executable, []),
    ('enterprise/agents/plugins/*', is_executable, [
        "chroot_version", "Dockerfile", "Makefile", "pyinstaller-deps.make", "chroot", "src",
        "cmk_update_agent.pyc", "pip-deps-32.make", "pip-deps.make", "dist",
        "cmk-update-agent.spec", "cmk-update-agent-32.spec", "build"
    ]),
    ('enterprise/alert_handlers/*', is_executable, []),
    ('enterprise/alert_handlers/*', is_executable, []),
]


def test_permissions() -> None:
    for pattern, check_func, excludes in _PERMISSIONS:
        git_dir = Path(cmk_path())
        for f in git_dir.glob(pattern):
            if not f.is_file():
                continue
            if f.name in excludes or f.name in _GLOBAL_EXCLUDES:
                continue
            assert check_func(f), "%s has wrong permissions (%r)" % (f, check_func)
