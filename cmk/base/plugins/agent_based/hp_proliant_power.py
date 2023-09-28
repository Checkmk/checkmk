#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import typing
from collections import abc

from cmk.base.plugins.agent_based.agent_based_api import v1
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils import hp_proliant


class Params(typing.TypedDict, total=True):
    levels: tuple[float, float] | None


Statuses = typing.Literal["other", "present", "absent"]

Section = tuple[Statuses, int]

STATUS_TABLE: typing.Final[abc.Mapping[str, Statuses]] = {
    # cpqHePowerMeterStatus
    # Description:        This value specifies whether Power Meter reading is supported by this Server .
    # The following values are supported:
    #    other(1) Could not read the Power Meter status.
    #    present(2) The Power Meter data is available.
    #    absent(3) The Power Meter data is not available at this time.
    "1": "other",
    "2": "present",
    "3": "absent",
}


def parse_hp_proliant_power(string_table: StringTable) -> Section | None:
    if not string_table:
        return None
    status_code, reading = string_table[0]
    return (STATUS_TABLE[status_code.strip()], int(reading))


v1.register.snmp_section(
    name="hp_proliant_power",
    parse_function=parse_hp_proliant_power,
    fetch=v1.SNMPTree(
        base=".1.3.6.1.4.1.232.6.2.15",
        oids=[
            "2",  # cpqHePowerMeterStatus
            "3",  # cpqHePowerMeterCurrReading
        ],
    ),
    detect=hp_proliant.DETECT,
)


def discover_hp_proliant_power(section: Section) -> DiscoveryResult:
    if section[0] != "absent":
        yield v1.Service()


def check_hp_proliant_power(params: Params, section: Section) -> CheckResult:
    status, reading = section
    if status != "present":
        yield v1.Result(state=v1.State.CRIT, summary=f"Power Meter state: {status}")
        return

    yield from v1.check_levels(
        value=reading,
        metric_name="watt",
        levels_upper=params.get("levels"),
        label="Current reading",
        render_func=lambda x: f"{x} Watts",
    )


v1.register.check_plugin(
    name="hp_proliant_power",
    service_name="HW Power Meter",
    check_function=check_hp_proliant_power,
    discovery_function=discover_hp_proliant_power,
    check_default_parameters={"levels": None},
)
