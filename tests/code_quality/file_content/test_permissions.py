#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import fnmatch
import os
from collections.abc import Callable
from pathlib import Path

import pytest

from tests.code_quality.utils import ChangedFiles
from tests.testlib.common.repo import repo_path


def is_executable(path: Path) -> bool:
    return os.access(path, os.X_OK)


def is_not_executable(path: Path) -> bool:
    return not os.access(path, os.X_OK)


_GLOBAL_EXCLUDES = (
    ".gitignore",
    ".f12",
    "OWNERS",
    "BUILD",
)

_PERMISSIONS = (
    # globbing pattern | check function | explicit excludes | exclude patterns
    ("active_checks/*", is_executable, ("BUILD", "check_mkevents.cc"), ()),
    ("agents/check_mk_agent.*", is_executable, ("check_mk_agent.spec",), ()),
    (
        "agents/plugins/*",
        is_executable,
        ("BUILD", "README", "Makefile", "__init__.py"),
        ("*.pyc",),
    ),
    ("notifications/*", is_executable, ("README", "debug"), ()),
    ("bin/*", is_executable, ("BUILD", "mkevent.cc", "mkeventd_open514.cc"), ()),
    # Enterprise specific
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
            "dev-requirements.in",
        ),
        (),
    ),
    ("omd/non-free/packages/alert-handling/alert_handlers/*", is_executable, (), ()),
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
    found_files = {
        f
        for f in repo_path().glob(pattern)
        if (
            f.is_file()
            and f.name not in explicit_excludes
            and f.name not in _GLOBAL_EXCLUDES
            and not any(fnmatch.fnmatch(f.name, p) for p in exclude_patterns)
        )
    }
    # see if we can update our test cases
    assert found_files

    tested_files = {f for f in found_files if changed_files.is_changed(f)}
    offending_files = {f for f in tested_files if not check_func(f)}

    assert not offending_files, f"{offending_files} have wrong permissions ({check_func!r})"


def _executable_iff_in_libexec(path: Path) -> bool:
    return ("libexec" in path.parts) is os.access(path, os.X_OK)


def test_plugin_family_permissions(changed_files: ChangedFiles) -> None:
    found_files = {
        f
        for f in repo_path().rglob("cmk/plugins/*")
        if f.is_file() and f.name not in _GLOBAL_EXCLUDES
    }
    # see if we can remove this test
    assert found_files

    tested_files = {f for f in found_files if changed_files.is_changed(f)}
    offending_files = {f for f in tested_files if not _executable_iff_in_libexec(f)}

    assert not offending_files, f"{offending_files} have wrong permissions"
