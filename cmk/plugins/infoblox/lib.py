#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.agent_based.v2 import any_of, CheckResult, contains, Metric, Result, startswith, State

DETECT_INFOBLOX = any_of(
    contains(".1.3.6.1.2.1.1.1.0", "infoblox"),
    startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.7779.1"),
)


def check_infoblox_statistics(ty: str, stats: Sequence[tuple[str, int, str, str]]) -> CheckResult:
    texts: dict[str, list[str]] = {}
    metrics = []
    for what, what_val, what_textfield, what_info in stats:
        texts.setdefault(what_textfield, []).append(f"{what_val} {what_info}")
        metrics.append(Metric(f"{ty}_{what}", what_val))

    yield Result(
        state=State.OK,
        summary=" - ".join(
            "{}: {}".format(what, ", ".join(entries)) for what, entries in texts.items()
        ),
    )
    yield from metrics
