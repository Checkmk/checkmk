#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
# There are different types of information. Can we handle them in a
# general way? There are:
#  - Percentage values
#  - Size values in KB
#  - Counters
#  - Rate counters (per second)
"""

from collections.abc import MutableMapping
from contextlib import suppress
from typing import Any

from cmk.agent_based.v2 import DiscoveryResult, get_rate, GetRateError, IgnoreResultsError, Service

Counters = dict[str, float]
Section = dict[tuple[str, str], Counters]


def discovery_mssql_counters_generic(
    section: Section,
    want_counters: set[str],
    dflt: dict[str, str] | None = None,
) -> DiscoveryResult:
    yield from (
        Service(item=f"{obj} {instance}", parameters=dflt)
        for (obj, instance), counters in section.items()
        if want_counters.intersection(counters)
    )


def get_rate_or_none(
    value_store: MutableMapping[str, Any],
    key: str,
    point_in_time: float,
    value: float,
) -> float | None:
    """This is a convienience function which handles exceptions and avoids structures like
    >> with suppress(GetRateError):
    >>    a = get_rate()
    >>    b = get_rate()
    >>    handle(a,b)
    which would lead to b being calculated on the third run rather the second
    """
    with suppress(GetRateError):
        return get_rate(value_store, key, point_in_time, value)
    return None


def get_int(mapping: Counters, key: str) -> int:
    """Try to return an int"""
    result = mapping.get(key)
    if isinstance(result, int):
        return result
    raise ValueError(f"Cannot handle {key!r}={result!r}")


def get_item(item: str, section: Section) -> tuple[Counters, str]:
    obj, instance, *counter = item.split()
    if (obj, instance) not in section:
        raise IgnoreResultsError("Item not found in monitoring data")
    return section[(obj, instance)], counter[0] if counter else ""
