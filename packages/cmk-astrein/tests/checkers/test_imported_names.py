#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast

import pytest

from cmk.astrein.checkers._imported_names import ImportedNames


def _resolve(source: str) -> str | None:
    tree = ast.parse(source)
    imported_names = ImportedNames()
    for statement in tree.body:
        if isinstance(statement, ast.Import | ast.ImportFrom):
            imported_names.record(statement)
    final_expression = tree.body[-1]
    assert isinstance(final_expression, ast.Expr)
    return imported_names.qualified_name(final_expression.value)


@pytest.mark.parametrize(
    "source, expected",
    [
        pytest.param("import a.b\na.b.c", "a.b.c", id="dotted_import_resolves_attribute_chain"),
        pytest.param("import a.b as x\nx", "a.b", id="aliased_dotted_import"),
        pytest.param("from a import b\nb", "a.b", id="from_import"),
        pytest.param("from a import b as y\ny", "a.b", id="from_import_alias"),
    ],
)
def test_resolves_imported_name_to_its_qualified_name(source: str, expected: str) -> None:
    assert _resolve(source) == expected


@pytest.mark.parametrize(
    "source",
    [
        pytest.param("unknown", id="unknown_name"),
        pytest.param("42", id="non_name_expression"),
        pytest.param("from . import b\nb", id="relative_import_not_tracked"),
    ],
)
def test_returns_none_when_name_cannot_be_resolved(source: str) -> None:
    assert _resolve(source) is None
