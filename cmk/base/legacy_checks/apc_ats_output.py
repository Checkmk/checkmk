#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import any_of, equals, SNMPTree


def parse_apc_ats_output(info):
    parsed = {}
    for index, voltage_str, current_str, perc_load_str, power_str in info:
        for key, value_str, factor in [
            ("voltage", voltage_str, 1),
            ("current", current_str, 0.1),
            ("perc_load", perc_load_str, 1),
            ("power", power_str, 1),
        ]:
            try:
                value = float(value_str) * factor
            except ValueError:
                continue
            instance = parsed.setdefault(index, {})
            instance[key] = value
    return parsed


def discover_apc_ats_output(parsed):
    yield from ((item, {}) for item in parsed)


def check_apc_ats_output(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    voltage = data.get("voltage")
    power = data.get("power")
    current = data.get("current")
    perc_load = data.get("perc_load")

    if voltage is not None:
        yield check_levels(
            voltage,
            "volt",
            params.get("output_voltage_max", (None, None))
            + params.get("output_voltage_min", (None, None)),
            infoname="Voltage",
            unit="V",
        )
    if power is not None:
        yield 0, "Power: %.2f W" % power

    if current is not None:
        yield 0, "Current: %.2f A" % current

    if perc_load is not None:
        yield check_levels(
            perc_load,
            "load_perc",
            params.get("load_perc_max", (None, None)) + params.get("load_perc_min", (None, None)),
            infoname="Load",
            unit="%",
        )


check_info["apc_ats_output"] = LegacyCheckDefinition(
    detect=any_of(
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.318.1.3.11"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.318.1.3.32"),
    ),
    parse_function=parse_apc_ats_output,
    discovery_function=discover_apc_ats_output,
    check_function=check_apc_ats_output,
    check_ruleset_name="apc_ats_output",
    service_name="Phase %s output",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.8.5.4.3.1",
        oids=["1", "3", "4", "10", "13"],
    ),
    check_default_parameters={
        "output_voltage_max": (240, 250),
        "load_perc_max": (85, 95),
    },
)
