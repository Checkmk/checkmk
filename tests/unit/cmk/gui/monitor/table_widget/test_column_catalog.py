#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from dataclasses import dataclass

import pytest

from cmk.gui.monitor.table_widget import ColumnCatalog, InvalidSortError, TableColumn
from cmk.web.utils.speaklater import LazyString


class _Field(enum.StrEnum):
    SIZE = "size"


class _Column(enum.StrEnum):
    NAME = "name"
    SIZE = "size"


@dataclass(frozen=True)
class _Sort:
    column: _Column


def _parse_sort(values: list[str]) -> list[_Sort]:
    return [_Sort(_Column(value)) for value in values]


_COLUMNS = {
    "name": TableColumn(LazyString(str, "Name")),
    "size": TableColumn(LazyString(str, "Size"), _Field.SIZE),
}

_CATALOG = ColumnCatalog(_COLUMNS, _parse_sort, [_Sort(_Column.NAME)])


def test_the_title_of_a_column_is_its_text() -> None:
    assert _CATALOG.title("size") == "Size"


def test_only_the_fields_of_the_shown_columns_are_queried() -> None:
    assert _CATALOG.fields(["name"]) == frozenset()
    assert _CATALOG.fields(["name", "size"]) == {_Field.SIZE}


def test_without_a_sort_the_default_sort_applies() -> None:
    assert _CATALOG.sorters(["name"], []) == [_Sort(_Column.NAME)]


def test_without_a_sort_and_a_default_sort_the_table_stays_unsorted() -> None:
    assert ColumnCatalog(_COLUMNS, _parse_sort).sorters(["name"], []) == []


@pytest.mark.parametrize(
    "sort, message",
    [
        pytest.param(["no_such_column"], "no_such_column", id="unknown column"),
        pytest.param(["size"], "Only a displayed column can sort the table", id="column not shown"),
    ],
)
def test_a_sort_the_table_cannot_apply_is_rejected(sort: list[str], message: str) -> None:
    with pytest.raises(InvalidSortError, match=message):
        _CATALOG.sorters(["name"], sort)


@pytest.mark.parametrize(
    "columns, message",
    [
        pytest.param(["name", "no_such_column"], "Unknown columns: no_such_column", id="unknown"),
        pytest.param(["name", "name"], "must not be repeated", id="repeated column"),
    ],
)
def test_columns_the_table_cannot_show_are_rejected(columns: list[str], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        _CATALOG.validate(columns, [])
