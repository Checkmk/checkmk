#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.monitor.hosts._models import HostSort, HostSortColumn, HostSortDirection


def parse_sort(value: object) -> list[HostSort]:
    """Parse the repeated ``sort`` query param into :class:`HostSort` objects.

    Each value defines one sort column; multiple values define a multi-column sort applied in the
    given priority order. An empty list means no sort. The same column must not be repeated. Any
    ``ValueError`` raised here is turned into a 400 response by the API framework.
    """
    if not isinstance(value, list):
        raise ValueError(f"Expected a list of sort values, got {type(value).__name__!r}.")
    sorts = [_parse_sort_token(token) for token in value]
    seen: set[HostSortColumn] = set()
    for sort in sorts:
        if sort.column in seen:
            raise ValueError(f"Column {sort.column.value!r} appears more than once in the sort.")
        seen.add(sort.column)
    return sorts


def _parse_sort_token(token: object) -> HostSort:
    """Parse a single ``column:direction`` query value into a :class:`HostSort`."""
    if not isinstance(token, str):
        raise ValueError(f"Expected a 'column:direction' string, got {type(token).__name__!r}.")

    column, separator, direction = token.partition(":")
    if not separator:
        raise ValueError(f"Expected a 'column:direction' value, got {token!r}.")
    try:
        sort_column = HostSortColumn(column)
    except ValueError:
        raise ValueError(
            f"Unknown sort column in {token!r}. Allowed columns: {HostSortColumn.options()}."
        ) from None
    try:
        sort_direction = HostSortDirection(direction)
    except ValueError:
        raise ValueError(
            f"Unknown sort direction in {token!r}. Allowed directions: {HostSortDirection.options()}."
        ) from None
    return HostSort(column=sort_column, direction=sort_direction)
