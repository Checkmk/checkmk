#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from collections.abc import Mapping, Sequence

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import CheckResult, render, Result, State, StringTable

MerakiAPIData = Mapping[str, object]


def load_json(string_table: StringTable) -> Sequence[MerakiAPIData]:
    try:
        return json.loads(string_table[0][0])
    except (IndexError, json.decoder.JSONDecodeError):
        return []


def check_last_reported_ts(
    last_reported_ts: float,
    levels_upper: tuple[int, int] | None = None,
    as_metric: bool = False,
) -> CheckResult:
    if (age := time.time() - last_reported_ts) < 0:
        yield Result(
            state=State.OK,
            summary="Negative timespan since last report time.",
        )
        return

    yield from check_levels_v1(
        value=age,
        label="Time since last report",
        metric_name="last_reported" if as_metric else None,
        levels_upper=levels_upper,
        render_func=render.timespan,
    )
