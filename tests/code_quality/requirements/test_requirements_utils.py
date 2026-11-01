#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pathlib import Path

import pytest

from tests.code_quality.requirements.utils import collect_third_party_imports

_SOURCE = """\
import typing
from typing import TYPE_CHECKING

import plain_import

if TYPE_CHECKING:
    import guarded_import
    from guarded_from import Thing

    try:
        import nested_in_guard
    except ImportError:
        pass
else:
    import else_branch_import

if typing.TYPE_CHECKING:
    import attribute_guarded_import

if not TYPE_CHECKING:
    import negated_guard_import
"""

_RUNTIME = {"plain-import", "else-branch-import", "negated-guard-import"}
_TYPE_CHECKING_ONLY = {
    "guarded-import",
    "guarded-from",
    "nested-in-guard",
    "attribute-guarded-import",
}


@pytest.fixture(name="source_file")
def fixture_source_file(tmp_path: Path) -> str:
    path = tmp_path / "module.py"
    path.write_text(_SOURCE)
    return str(path)


def test_runtime_only_skips_type_checking_blocks(source_file: str) -> None:
    assert collect_third_party_imports([source_file], runtime_only=True) == _RUNTIME


def test_all_imports_include_type_checking_blocks(source_file: str) -> None:
    assert collect_third_party_imports([source_file]) == _RUNTIME | _TYPE_CHECKING_ONLY
