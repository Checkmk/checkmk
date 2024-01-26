#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
from collections.abc import Mapping
from typing import Callable

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    check_levels,
    get_value_store,
    register,
    Result,
    Service,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils import netapp_ontap_models as models
from cmk.base.plugins.agent_based.utils.temperature import check_temperature, TempParamDict

Section = Mapping[
    str, models.EnvironmentDiscreteSensorModel | models.EnvironmentThresholdSensorModel
]
DiscreteSection = Mapping[str, models.EnvironmentDiscreteSensorModel]
ThresholdSection = Mapping[str, models.EnvironmentThresholdSensorModel]


def parse_netapp_ontap_environment(string_table: StringTable) -> Section:
    return {
        f"{discriminator.sensor.node_name} / {discriminator.sensor.name}": discriminator.sensor
        for line in string_table
        if (
            discriminator := models.DiscrimnatorEnvSensorModel.validate(
                {"sensor": json.loads(line[0])}
            )
        )
    }


register.agent_section(
    name="netapp_ontap_environment",
    parse_function=parse_netapp_ontap_environment,
)


def discover_netapp_ontap_environment(
    predicate: Callable | None = None,
) -> Callable[[Section], DiscoveryResult]:
    def _discover(section: Section) -> DiscoveryResult:
        for item_name, values in section.items():
            if predicate is None:
                yield Service(item=item_name)
            elif predicate(values):
                yield Service(item=item_name)
            else:
                continue

    return _discover


def check_netapp_ontap_environment_discrete(
    item: str, params: None, section: DiscreteSection
) -> CheckResult:
    if not (data := section.get(item)):
        return

    yield Result(
        state=State.OK if data.discrete_state == "normal" else State.CRIT,
        summary=f"Sensor state: {data.discrete_state}, Sensor value: {data.discrete_value}",
    )


def check_netapp_ontap_environment_threshold(
    item: str, params: TempParamDict, section: ThresholdSection
) -> CheckResult:
    def _perf_key(_key):
        return _key.replace("/", "").replace(" ", "_").replace("__", "_").lower()

    # We don't want mV or mA, but V or A
    def _scale(val, _unit):
        if val is not None and _unit.lower() in ("mv", "ma"):
            val /= 1000.0
        return val

    def _scale_unit(_unit):
        return {"mv": "v", "ma": "a"}.get(_unit.lower(), _unit.lower())

    if (data := section.get(item)) is None:
        return

    levels = (
        _scale(data.warning_high_threshold, data.value_units),
        _scale(data.critical_high_threshold, data.value_units),
        _scale(data.warning_low_threshold, data.value_units),
        _scale(data.critical_low_threshold, data.value_units),
    )

    if data.sensor_type == "thermal":
        yield from check_temperature(
            reading=_scale(data.value, data.value_units),
            params=params,
            unique_name=_perf_key(f"netapp_environment_thermal_{data.name}"),
            dev_unit=_scale_unit(data.value_units),
            dev_levels=levels[:2],
            dev_levels_lower=levels[2:],
            value_store=get_value_store(),
        )
        return

    def _fan_render(v):
        return f"{int(v)}" if data and data.sensor_type == "fan" else f"{v}"

    yield from check_levels(
        value=_scale(data.value, data.value_units),
        levels_upper=levels[:2],
        levels_lower=levels[2:],
        metric_name=data.sensor_type,
        # we don't want to see decimal rpms
        # we want to see the voltage and current in more detail
        render_func=_fan_render,
    )


register.check_plugin(
    name="netapp_ontap_environment",
    service_name="PSU Controller %s",
    discovery_function=discover_netapp_ontap_environment(
        lambda v: v.name.startswith("PSU") and v.name.endswith(" FAULT")
    ),
    check_function=check_netapp_ontap_environment_discrete,
    check_ruleset_name="hw_psu",
    check_default_parameters={},
)


register.check_plugin(
    name="netapp_ontap_environment_fan_faults",
    sections=["netapp_ontap_environment"],
    service_name="Fan Controller %s",
    discovery_function=discover_netapp_ontap_environment(
        lambda v: "fan" in v.name.lower() and v.name.endswith(" Fault")
    ),
    check_function=check_netapp_ontap_environment_discrete,
    check_ruleset_name="hw_psu",
    check_default_parameters={},
)


register.check_plugin(
    name="netapp_ontap_environment_temperature",
    service_name="System Temperature %s",
    sections=["netapp_ontap_environment"],
    discovery_function=discover_netapp_ontap_environment(lambda v: v.sensor_type == "thermal"),
    check_function=check_netapp_ontap_environment_threshold,
    check_ruleset_name="temperature",
    check_default_parameters={},
)

register.check_plugin(
    name="netapp_ontap_environment_fans",
    service_name="System Fans %s",
    sections=["netapp_ontap_environment"],
    discovery_function=discover_netapp_ontap_environment(lambda v: v.sensor_type == "fan"),
    check_function=check_netapp_ontap_environment_threshold,
    check_ruleset_name="hw_fans",
    check_default_parameters={"lower": (2000, 1000)},
)


register.check_plugin(
    name="netapp_ontap_environment_voltage",
    service_name="System Voltage %s",
    sections=["netapp_ontap_environment"],
    discovery_function=discover_netapp_ontap_environment(lambda v: v.sensor_type == "voltage"),
    check_function=check_netapp_ontap_environment_threshold,
    check_ruleset_name="voltage",
    check_default_parameters={},
)

register.check_plugin(
    name="netapp_ontap_environment_current",
    service_name="System Currents %s",
    sections=["netapp_ontap_environment"],
    discovery_function=discover_netapp_ontap_environment(lambda v: v.sensor_type == "current"),
    check_function=check_netapp_ontap_environment_threshold,
    check_default_parameters={},
)
