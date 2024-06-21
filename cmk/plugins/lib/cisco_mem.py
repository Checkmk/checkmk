#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, MutableMapping
from contextlib import suppress
from typing import Any

from cmk.agent_based.v2 import (
    all_of,
    CheckResult,
    contains,
    exists,
    GetRateError,
    not_contains,
    Result,
    State,
)

from .memory import check_element, get_levels_mode_from_value
from .size_trend import size_trend

DETECT_MULTIITEM = all_of(
    contains(".1.3.6.1.2.1.1.1.0", "cisco"),
    not_contains(".1.3.6.1.2.1.1.1.0", "nx-os"),
    exists(".1.3.6.1.4.1.9.9.109.1.1.1.1.2.*"),
)


def check_cisco_mem_sub(
    value_store: MutableMapping[str, Any],
    item: str,
    params: Mapping[str, Any],
    mem_used: int,
    mem_total: int,
) -> CheckResult:
    if not mem_total:
        yield Result(
            state=State.UNKNOWN,
            summary="Cannot calculate memory usage: Device reports total memory 0",
        )
        return

    warn, crit = params.get("levels", (None, None))
    mode = get_levels_mode_from_value(warn)
    mega = 1024 * 1024
    if isinstance(warn, int):
        warn *= mega  # convert from megabyte to byte
        crit *= mega
    if warn is not None:
        warn = abs(warn)
        crit = abs(crit)

    yield from check_element(
        "Usage",
        mem_used,
        mem_total,
        (mode, (warn, crit)),
        create_percent_metric=True,
    )

    if params.get("trend_range"):
        with suppress(GetRateError):
            yield from size_trend(
                value_store=value_store,
                value_store_key=item,
                resource="memory",
                levels=params,
                used_mb=mem_used / mega,
                size_mb=mem_total / mega,
                timestamp=None,
            )
