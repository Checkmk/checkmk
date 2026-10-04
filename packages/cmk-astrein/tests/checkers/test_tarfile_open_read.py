#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from pathlib import Path

from cmk.astrein.checkers.tarfile_open_read import TarfileOpenReadChecker
from cmk.astrein.framework import CheckerError


def _check_tarfile(
    code: str,
    file_path: Path = Path("/repo/cmk/some_module.py"),
    repo_root: Path = Path("/repo"),
) -> list[CheckerError]:
    checker = TarfileOpenReadChecker(file_path, repo_root, code)
    return checker.check(ast.parse(code))


def test_tarfile_rejects_open_no_mode() -> None:
    errors = _check_tarfile('tarfile.open("f")')
    assert len(errors) == 1
    assert "tarfile.open()" in errors[0].message


def test_tarfile_rejects_open_read_mode_keyword() -> None:
    errors = _check_tarfile('tarfile.open("f", mode="r:gz")')
    assert len(errors) == 1


def test_tarfile_rejects_open_read_mode_positional() -> None:
    errors = _check_tarfile('tarfile.open("f", "r:bz2")')
    assert len(errors) == 1


def test_tarfile_rejects_tarfile_class() -> None:
    errors = _check_tarfile('TarFile.open("f")')
    assert len(errors) == 1


def test_tarfile_rejects_tf_suffix() -> None:
    errors = _check_tarfile('mytf.open("f")')
    assert len(errors) == 1


def test_tarfile_allows_write_mode() -> None:
    assert _check_tarfile('tarfile.open("f", mode="w")') == []


def test_tarfile_allows_write_mode_positional() -> None:
    assert _check_tarfile('tarfile.open("f", "w:gz")') == []


def test_tarfile_allows_other_object() -> None:
    assert _check_tarfile('foo.open("f")') == []


def test_tarfile_allows_excluded_tests_path() -> None:
    assert (
        _check_tarfile(
            'tarfile.open("f")',
            file_path=Path("/repo/tests/unit/test_foo.py"),
        )
        == []
    )


def test_tarfile_allows_excluded_package_tests_path() -> None:
    assert (
        _check_tarfile(
            'tarfile.open("f")',
            file_path=Path("/repo/packages/cmk-foo/tests/test_bar.py"),
        )
        == []
    )


def test_tarfile_allows_excluded_mkp_tool_path() -> None:
    assert (
        _check_tarfile(
            'tarfile.open("f")',
            file_path=Path("/repo/mkp_tool/something.py"),
        )
        == []
    )


def test_tarfile_allows_excluded_nested_mkp_tool_path() -> None:
    assert (
        _check_tarfile(
            'tarfile.open("f")',
            file_path=Path("/repo/packages/cmk-mkp-tool/cmk/mkp_tool/_mkp.py"),
        )
        == []
    )


def test_tarfile_allows_excluded_nested_testlib_path() -> None:
    assert (
        _check_tarfile(
            'tarfile.open("f")',
            file_path=Path("/repo/packages/cmk-agent-receiver/cmk/testlib/config.py"),
        )
        == []
    )
