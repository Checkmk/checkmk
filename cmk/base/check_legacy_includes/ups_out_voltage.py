#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckResult


def check_ups_out_voltage(
    item: str, params: Mapping[str, Any], info: Sequence[Sequence[str]]
) -> LegacyCheckResult:
    for line in info:
        if line[0] != item:
            continue
        yield check_levels(
            int(line[1]),
            "out_voltage",
            (None, None) + params["levels_lower"],
            human_readable_func=lambda v: f"{v}V",
            infoname="Out voltage",
        )
        return
