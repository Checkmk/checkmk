#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import NamedTuple

from cmk.agent_based.v2 import all_of, exists, startswith, State, StringTable

DETECT_QUANTA = all_of(
    startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072.3.2.10"),
    exists(".1.3.6.1.4.1.7244.1.2.1.1.1.0"),
)


class Item(NamedTuple):
    item: str
    status: tuple[State, str]
    name: str
    value: float | None
    lower_levels: tuple[float | None, float | None]
    upper_levels: tuple[float | None, float | None]


_STATUS_MAP: Mapping[str, tuple[State, str]] = {
    "1": (State.WARN, "other"),
    "2": (State.UNKNOWN, "unknown"),
    "3": (State.OK, "OK"),
    "4": (State.WARN, "non critical upper"),
    "5": (State.CRIT, "critical upper"),
    "6": (State.CRIT, "non recoverable upper"),
    "7": (State.WARN, "non critical lower"),
    "8": (State.CRIT, "critical lower"),
    "9": (State.CRIT, "non recoverable lower"),
    "10": (State.CRIT, "failed"),
}


def _translate_dev_status(status: str) -> tuple[State, str]:
    return _STATUS_MAP.get(status, (State.UNKNOWN, f"unknown[{status}]"))


def _validate_levels(
    dev_warn: str,
    dev_crit: str,
) -> tuple[float | None, float | None]:
    # If this value cannot be determined by software, then a value of -99 will be returned
    if dev_crit and dev_crit != "-99":
        crit: float | None = float(dev_crit)
    else:
        crit = None

    if dev_warn and dev_warn != "-99":
        warn: float | None = float(dev_warn)
    elif crit is not None:
        warn = crit
    else:
        warn = None

    return warn, crit


def parse_quanta(string_table: Sequence[StringTable]) -> Mapping[str, Item]:
    parsed: dict[str, Item] = {}
    for (
        dev_index,
        dev_status,
        dev_name,
        dev_value,
        dev_upper_crit,
        dev_upper_warn,
        dev_lower_warn,
        dev_lower_crit,
    ) in string_table[0]:
        try:
            value: float | None = float(dev_value)
        except ValueError:
            value = None

        # device name can be hex value in the snmp walk
        # auto conversion to string seems to miss 'x01'
        name = dev_name.replace("\x01", "")

        item = Item(
            dev_index,
            _translate_dev_status(dev_status),
            name,
            value,
            _validate_levels(dev_lower_warn, dev_lower_crit),
            _validate_levels(dev_upper_warn, dev_upper_crit),
        )
        parsed.setdefault(name, item)

    return parsed
