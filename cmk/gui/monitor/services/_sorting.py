#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import functools
import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any, assert_never

from ._models import Service, ServiceSort, ServiceSortColumn, ServiceSortDirection

_NEVER_CHECKED = 0


def service_sorter(sorters: Sequence[ServiceSort]) -> Callable[[Service], Any]:
    """Build a sort key for the requested sorters, or for the page default if there are none.

    An empty list is not "leave the order alone": it is what the page sends while the user has
    not sorted a column, and that state leads with Checkmk's own services. Every explicitly
    requested sorter is taken literally instead, so sorting by name ascending really is a plain
    natural sort.
    """
    if not sorters:
        return functools.cmp_to_key(lambda a, b: compare_service_names(a.name, b.name))

    def _get_value(service: Service, column: ServiceSortColumn) -> Any:
        match column:
            case ServiceSortColumn.NAME:
                return service.name
            case ServiceSortColumn.STATE:
                return service.state
            case ServiceSortColumn.SUMMARY:
                return service.summary
            case ServiceSortColumn.LAST_CHECK:
                return service.last_check or _NEVER_CHECKED
            case ServiceSortColumn.LAST_STATE_CHANGE:
                return service.last_state_change
            case _:
                assert_never(column)

    def _compare(a: Service, b: Service) -> int:
        for sorter in sorters:
            val_a = _get_value(a, sorter.column)
            val_b = _get_value(b, sorter.column)
            if sorter.column.natural_sort:
                result = sort_naturally(val_a, val_b)
            elif val_a < val_b:
                result = -1
            elif val_a > val_b:
                result = 1
            else:
                result = 0
            if result == 0:
                continue
            return result if sorter.direction == ServiceSortDirection.ASC else -result
        return 0

    return functools.cmp_to_key(_compare)


_DIGIT_REGEX = re.compile(r"(\d+)")
type NaturalSortChunk = int | str


def sort_naturally(a: str, b: str) -> int:
    keys_a, keys_b = _natural_sort_keys(a), _natural_sort_keys(b)
    return (keys_a > keys_b) - (keys_a < keys_b)


def _natural_sort_keys(s: str) -> tuple[tuple[NaturalSortChunk, ...], tuple[NaturalSortChunk, ...]]:
    # Split into alternating text/digit chunks, e.g. "CPU load 07x" -> ["CPU load ", "07", "x"].
    chunks = [int(chunk) if chunk.isdigit() else str(chunk) for chunk in _DIGIT_REGEX.split(s)]
    sort_key = tuple(chunk.lower() if isinstance(chunk, str) else chunk for chunk in chunks)
    tiebreak_key = tuple(chunks)
    return sort_key, tiebreak_key


_SERVICE_NAME_RANKS: Mapping[str, int] = {
    "Check_MK": 0,
    "Check_MK Agent": 1,
    "Check_MK Discovery": 2,
    "Check_MK inventory": 3,
    "Check_MK HW/SW Inventory": 4,
}


def compare_service_names(a: str, b: str) -> int:
    """Compare service names: Checkmk's own first, everything else naturally."""
    rank_a, rank_b = (
        _SERVICE_NAME_RANKS.get(a, len(_SERVICE_NAME_RANKS)),
        _SERVICE_NAME_RANKS.get(b, len(_SERVICE_NAME_RANKS)),
    )
    return (rank_a > rank_b) - (rank_a < rank_b) or sort_naturally(a, b)
