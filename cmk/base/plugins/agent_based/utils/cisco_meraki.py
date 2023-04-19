#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from collections.abc import Mapping, Sequence

from ..agent_based_api.v1 import render, Result, State
from ..agent_based_api.v1.type_defs import CheckResult, StringTable

MerakiAPIData = Mapping[str, object]


def load_json(string_table: StringTable) -> Sequence[MerakiAPIData]:
    try:
        return json.loads(string_table[0][0])
    except (IndexError, json.decoder.JSONDecodeError):
        return []


def check_last_reported_ts(last_reported_ts: float) -> CheckResult:
    if (age := time.time() - last_reported_ts) < 0:
        yield Result(
            state=State.OK,
            summary="Negative timespan since last report time.",
        )
        return

    yield Result(
        state=State.OK,
        summary=f"Time since last report: {render.timespan(age)}",
    )
