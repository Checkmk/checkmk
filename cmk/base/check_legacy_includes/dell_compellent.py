#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import DiscoveryResult, Service, StringTable


def discover(string_table: StringTable) -> DiscoveryResult:
    for item, *_rest in string_table:
        yield Service(item=item)


_STATE_MAP: Mapping[str, tuple[int, str]] = {
    "1": (0, "UP"),
    "2": (2, "DOWN"),
    "3": (1, "DEGRADED"),
}


def dev_state_map(orig_dev_state: str) -> tuple[int, str]:
    return _STATE_MAP.get(orig_dev_state, (3, f"unknown[{orig_dev_state}]"))
