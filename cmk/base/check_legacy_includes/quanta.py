#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import MutableMapping, Sequence
from typing import NamedTuple


class Item(NamedTuple):
    item: str
    status: tuple[int, str]
    name: str
    value: float | None
    lower_levels: tuple[float | None, float | None]
    upper_levels: tuple[float | None, float | None]


def _translate_dev_status(status: str) -> tuple[int, str]:
    status_dict = {
        "1": (1, "other"),
        "2": (3, "unknown"),
        "3": (0, "OK"),
        "4": (1, "non critical upper"),
        "5": (2, "critical upper"),
        "6": (2, "non recoverable upper"),
        "7": (1, "non critical lower"),
        "8": (2, "critical lower"),
        "9": (2, "non recoverable lower"),
        "10": (2, "failed"),
    }

    return status_dict.get(status, (3, "unknown[%s]" % status))


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


def parse_quanta(info: Sequence[Sequence[Sequence[str]]]) -> MutableMapping[str, Item]:
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
    ) in info[0]:
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
