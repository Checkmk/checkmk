#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from pathlib import Path

import pytest

from cmk.astrein.checker_simple_patterns import ConftestImportChecker
from cmk.astrein.framework import CheckerError


def _check(code: str) -> list[CheckerError]:
    repo_root = Path("/repo")
    checker = ConftestImportChecker(repo_root / "tests" / "test_x.py", repo_root, code)
    return checker.check(ast.parse(code))


@pytest.mark.parametrize(
    "code",
    [
        pytest.param("from conftest import helper", id="bare"),
        pytest.param("from .conftest import helper", id="relative"),
        pytest.param("from ..conftest import helper", id="relative_parent"),
        pytest.param("from tests.unit.cmk.conftest import helper", id="absolute"),
        pytest.param("import conftest", id="import_module"),
        pytest.param("import tests.unit.conftest", id="import_dotted"),
        pytest.param("from . import conftest", id="from_package_import_conftest"),
        pytest.param("from ..sub import conftest", id="from_parent_package_import_conftest"),
        pytest.param("from tests.unit import conftest as fixtures", id="import_conftest_aliased"),
    ],
)
def test_conftest_import_is_rejected(code: str) -> None:
    errors = _check(code)
    assert len(errors) == 1
    assert errors[0].checker_id == "conftest-import"


@pytest.mark.parametrize(
    "code",
    [
        pytest.param("from tests.testlib.site import Site", id="testlib"),
        pytest.param("from my_conftest_helpers import helper", id="similar_name"),
        pytest.param("from mypkg.conftests import helper", id="plural_near_miss"),
        pytest.param("from tests.unit.conftest_utils import helper", id="dotted_near_miss"),
        pytest.param("from mypkg import conftests", id="plural_name_near_miss"),
        pytest.param("import pytest", id="pytest"),
    ],
)
def test_other_imports_are_allowed(code: str) -> None:
    assert _check(code) == []
