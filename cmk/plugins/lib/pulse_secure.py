#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import contains, StringTable

DETECT_PULSE_SECURE = contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12532")


def parse_pulse_secure(string_table: StringTable, *keys: str) -> Mapping[str, int] | None:
    if not string_table:
        return None
    parsed = {}
    for key, value in zip(keys, string_table[0]):
        try:
            parsed[key] = int(value)
        except ValueError:
            pass
    return parsed
