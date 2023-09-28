#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from .agent_based_api.v1 import get_value_store, register, Service, SNMPTree
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.primekey import DETECT_PRIMEKEY
from .utils.temperature import check_temperature, TempParamDict

_Section = Mapping[str, float]


def parse(string_table: StringTable) -> _Section | None:
    if not string_table:
        return None

    # add constant item key to be able to use existing temperature ruleset
    return {"CPU": float(string_table[0][0])}


register.snmp_section(
    name="primekey_cpu_temperature",
    parse_function=parse,
    detect=DETECT_PRIMEKEY,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.22408.1.1.2.1.3.99.112.117",
        oids=[
            "1",  # cpuTemp
        ],
    ),
)


def discover(section: _Section) -> DiscoveryResult:
    for item in section.keys():
        yield Service(item=item)


def check(
    item: str,
    params: TempParamDict,
    section: _Section,
) -> CheckResult:
    if not (temperature := section.get(item)):
        return

    yield from check_temperature(
        params=params,
        reading=temperature,
        unique_name=f"PrimeKey {item} Temperature",
        value_store=get_value_store(),
    )


register.check_plugin(
    name="primekey_cpu_temperature",
    service_name="Temperature PrimeKey %s",
    discovery_function=discover,
    check_function=check,
    check_default_parameters=TempParamDict({"levels": (20.0, 50.0)}),
    check_ruleset_name="temperature",
)
