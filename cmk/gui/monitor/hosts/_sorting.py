#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools
import re
from collections.abc import Callable, Sequence
from typing import Any, assert_never

from ._models import Host, HostSort, HostSortColumn, HostSortDirection


def host_sorter(sorters: Sequence[HostSort]) -> Callable[[Host], Any]:
    def _get_value(host: Host, column: HostSortColumn) -> Any:
        match column:
            case HostSortColumn.NAME:
                return host.name
            case HostSortColumn.ALIAS:
                return host.alias
            case HostSortColumn.ADDRESS:
                return host.address
            case HostSortColumn.STATE:
                return host.state
            case HostSortColumn.NUM_SERVICES:
                return host.service_counts.total
            case HostSortColumn.NUM_SERVICES_OK:
                return host.service_counts.ok
            case HostSortColumn.NUM_SERVICES_WARN:
                return host.service_counts.warn
            case HostSortColumn.NUM_SERVICES_CRIT:
                return host.service_counts.crit
            case HostSortColumn.NUM_SERVICES_UNKNOWN:
                return host.service_counts.unknown
            case HostSortColumn.NUM_SERVICES_PENDING:
                return host.service_counts.pending
            case _:
                assert_never(column)

    def _compare(a: Host, b: Host) -> int:
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
            return result if sorter.direction == HostSortDirection.ASC else -result
        return 0

    return functools.cmp_to_key(_compare)


_DIGIT_REGEX = re.compile(r"(\d+)")
type NaturalSortChunk = int | str


def sort_naturally(a: str, b: str) -> int:
    keys_a, keys_b = _natural_sort_keys(a), _natural_sort_keys(b)
    return (keys_a > keys_b) - (keys_a < keys_b)


def _natural_sort_keys(s: str) -> tuple[tuple[NaturalSortChunk, ...], tuple[NaturalSortChunk, ...]]:
    # Split into alternating text/digit chunks, e.g. "Host07x" -> ["Host", "07", "x"].
    chunks = [int(chunk) if chunk.isdigit() else str(chunk) for chunk in _DIGIT_REGEX.split(s)]
    sort_key = tuple(chunk.lower() if isinstance(chunk, str) else chunk for chunk in chunks)
    tiebreak_key = tuple(chunks)
    return sort_key, tiebreak_key
