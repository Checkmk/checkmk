#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Any

from cmk.agent_based.v2 import StringTable

PrismAPIData = dict[str, Any]

PRISM_POWER_STATES = {
    "on": 0,
    "unknown": 3,
    "off": 1,
    "powering_on": 0,
    "shutting_down": 1,
    "powering_off": 1,
    "pausing": 1,
    "paused": 1,
    "suspending": 1,
    "suspended": 1,
    "resuming": 0,
    "resetting": 1,
    "migrating": 0,
}


def load_json(string_table: StringTable) -> PrismAPIData:
    try:
        return json.loads(string_table[0][0])
    except (IndexError, json.decoder.JSONDecodeError):
        return {}
