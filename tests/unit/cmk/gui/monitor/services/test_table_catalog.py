#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.monitor.services.table import HOST_SERVICES_TABLE, ServiceOptionalField
from cmk.gui.monitor.table_widget import InvalidSortError


def test_only_the_optional_fields_of_the_shown_columns_are_queried() -> None:
    assert HOST_SERVICES_TABLE.fields(["state", "name", "labels", "groups"]) == {
        ServiceOptionalField.LABELS,
        ServiceOptionalField.GROUPS,
    }


def test_a_shown_column_sorts_the_table() -> None:
    sorters = HOST_SERVICES_TABLE.sorters(["state", "name"], ["state:desc"])

    assert [str(sorter) for sorter in sorters] == ["state:desc"]


@pytest.mark.parametrize(
    "sort",
    [
        pytest.param(["no_such_column:asc"], id="unknown column"),
        pytest.param(["summary:asc"], id="column not shown"),
    ],
)
def test_a_sort_the_table_cannot_apply_is_rejected(sort: list[str]) -> None:
    with pytest.raises(InvalidSortError):
        HOST_SERVICES_TABLE.sorters(["state", "name"], sort)


def test_an_unknown_column_is_rejected() -> None:
    with pytest.raises(ValueError, match="no_such_column"):
        HOST_SERVICES_TABLE.validate(["name", "no_such_column"], [])
