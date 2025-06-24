#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import fnmatch
import os
from collections.abc import Callable
from pathlib import Path

import pytest

from tests.testlib.common.repo import repo_path

from tests.code_quality.utils import ChangedFiles


def is_executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def is_not_executable(path: Path) -> bool:
    return path.is_file() and not os.access(path, os.X_OK)


_GLOBAL_EXCLUDES = (
    ".gitignore",
    ".f12",
)

_PERMISSIONS = (
    # globbing pattern                check function,   explicit excludes, exclude patterns
    ("active_checks/*", is_executable, ("Makefile", "check_mkevents.cc"), ()),
    ("agents/check_mk_agent.*", is_executable, ("check_mk_agent.spec",), ()),
    (
        "agents/plugins/*",
        is_executable,
        ("BUILD", "README", "Makefile", "__init__.py"),
        ("*.checksum", "*.pyc", "*_2.py"),
    ),
    ("cmk/plugins/*/agent_based/*", is_not_executable, (), ()),
    ("cmk/plugins/*/bakery/*", is_not_executable, (), ()),
    ("cmk/plugins/*/graphing/*", is_not_executable, (), ()),
    ("cmk/plugins/*/libexec/*", is_executable, (), ()),
    ("cmk/plugins/*/manpages/*", is_not_executable, (), ()),
    ("cmk/plugins/*/manpages/*/*", is_executable, (), ()),  # THIS SHOULD FAIL
    ("cmk/plugins/*/rulesets/*", is_not_executable, (), ()),
    ("cmk/plugins/*/server_side_calls/*", is_not_executable, (), ()),
    ("pnp-templates/*", is_not_executable, (), ()),
    ("notifications/*", is_executable, ("README", "debug"), ()),
    ("bin/*", is_executable, ("Makefile", "mkevent.cc", "mkeventd_open514.cc"), ()),
    # Enterprise specific
    ("omd/packages/enterprise/bin/*", is_executable, (), ()),
    ("omd/packages/enterprise/active_checks/*", is_executable, (), ()),
    (
        "non-free/packages/cmk-update-agent/*",
        is_executable,
        (
            "chroot_version",
            "Dockerfile",
            "Makefile",
            "pyinstaller-deps.make",
            "chroot",
            "src",
            "cmk_update_agent.pyc",
            "pip-deps-32.make",
            "pip-deps.make",
            "dist",
            "cmk-update-agent.spec",
            "cmk-update-agent-32.spec",
            "build",
            "BUILD",
            "pyproject.toml",
            "ci.json",
        ),
        (),
    ),
    ("omd/packages/enterprise/alert_handlers/*", is_executable, (), ()),
)


@pytest.mark.parametrize(
    ["pattern", "check_func", "explicit_excludes", "exclude_patterns"],
    _PERMISSIONS,
)
def test_permissions(
    changed_files: ChangedFiles,
    pattern: str,
    check_func: Callable[[Path], bool],
    explicit_excludes: tuple[str, ...],
    exclude_patterns: tuple[str, ...],
) -> None:
    for f in repo_path().glob(pattern):
        if not f.is_file() or not changed_files.is_changed(f):
            continue
        if f.name in explicit_excludes or f.name in _GLOBAL_EXCLUDES:
            continue
        if any(fnmatch.fnmatch(f.name, p) for p in exclude_patterns):
            continue
        assert check_func(f), f"{f} has wrong permissions ({check_func!r})"
