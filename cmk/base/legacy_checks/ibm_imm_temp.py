#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator, Mapping
from typing import Any

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.temperature import check_temperature, TempParamType
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.ibm_imm_temp import SensorTemperature


def inventory_ibm_imm_temp(section: Mapping[str, SensorTemperature]) -> Iterator[Any]:
    yield from ((item, {}) for item in section if section[item].temperature != 0.0)


def check_ibm_imm_temp(
    item: str, params: TempParamType, section: Mapping[str, SensorTemperature]
) -> tuple | None:
    if not (temperature := section.get(item)):
        return None

    return check_temperature(
        temperature.temperature,
        params,
        "ibm_imm_temp_%s" % item,
        dev_levels=temperature.upper_device_levels,
        dev_levels_lower=temperature.lower_device_levels,
    )


check_info["ibm_imm_temp"] = LegacyCheckDefinition(
    service_name="Temperature %s",
    discovery_function=inventory_ibm_imm_temp,
    check_function=check_ibm_imm_temp,
    check_ruleset_name="temperature",
)
