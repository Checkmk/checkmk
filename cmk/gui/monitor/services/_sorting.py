#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import datetime as dt
import functools
import re
from collections.abc import Callable, Sequence
from typing import Any, assert_never

from ._models import Service, ServiceSort, ServiceSortColumn, ServiceSortDirection

_NEVER_CHECKED = dt.datetime.min.replace(tzinfo=dt.UTC)


def service_sorter(sorters: Sequence[ServiceSort]) -> Callable[[Service], Any]:
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
