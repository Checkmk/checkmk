#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from typing import Mapping

from .agent_based_api.v1 import Attributes, register
from .agent_based_api.v1.type_defs import InventoryResult, StringTable

Section = Mapping[str, Mapping[str, str]]


# No idea why we need this. Devices respond with '10 Â°C'.
_FIXUP_ENCODING = (("°".encode("utf-8").decode("latin-1"), "°"),)


def parse_allnet_ip_sensoric(string_table: StringTable) -> Section:
    """parses agent output in a structure like:
    {'sensor0': {'alarm0': '0',
              'all4000_typ': '0',
              'function': '1',
              'limit_high': '50.00',
              'limit_low': '10.00',
              'maximum': '28.56',
              'minimum': '27.43',
              'name': 'Temperatur intern',
              'value_float': '27.50',
              'value_int': '2750',
              'value_string': '27.50'},
    [...]
    'system': {'alarmcount': '4',
             'date': '30.06.2014',
             'devicename': 'all5000',
             'devicetype': 'ALL5000',
             'sys': '116240',
             'time': '16:57:50'}}
    """
    pat = re.compile(r"(\w+)\.(\w+)")
    parsed: dict[str, dict[str, str]] = {}
    for key, value in string_table:
        if not (match := pat.search(key)):
            continue

        for wrong, right in _FIXUP_ENCODING:
            value = value.replace(wrong, right)

        sensor = match.group(1)
        field = match.group(2)
        parsed.setdefault(sensor, {})[field] = value

    return parsed


register.agent_section(
    name="allnet_ip_sensoric",
    parse_function=parse_allnet_ip_sensoric,
)


def inventory_allnet_ip_sensoric(section: Mapping[str, Mapping[str, str]]) -> InventoryResult:

    if model := section.get("system", {}).get("devicetype"):
        yield Attributes(
            path=["hardware", "system"],
            inventory_attributes={"model": model},
        )


register.inventory_plugin(
    name="allnet_ip_sensoric",
    inventory_function=inventory_allnet_ip_sensoric,
)
