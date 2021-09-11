#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
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

from contextlib import suppress
from typing import Any, Dict, MutableMapping, Optional, Set, Tuple

from ..agent_based_api.v1 import get_rate, GetRateError, IgnoreResultsError, Service
from ..agent_based_api.v1.type_defs import DiscoveryResult

Counters = Dict[str, float]
Section = Dict[Tuple[str, str], Counters]


def discovery_mssql_counters_generic(
    section: Section,
    want_counters: Set[str],
    dflt: Optional[Dict[str, str]] = None,
) -> DiscoveryResult:
    yield from (
        Service(item="%s %s" % (obj, instance), parameters=dflt)
        for (obj, instance), counters in section.items()
        if want_counters.intersection(counters)
    )


def get_rate_or_none(
    value_store: MutableMapping[str, Any],
    key: str,
    point_in_time: float,
    value: float,
) -> Optional[float]:
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
    raise ValueError("Cannot handle %r=%r" % (key, result))


def get_item(item: str, section: Section) -> Tuple[Counters, str]:
    obj, instance, *counter = item.split()
    if (obj, instance) not in section:
        raise IgnoreResultsError("Item not found in monitoring data")
    return section[(obj, instance)], counter[0] if counter else ""
