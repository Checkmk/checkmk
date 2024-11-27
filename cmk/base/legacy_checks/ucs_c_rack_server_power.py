#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# exemplary output of special agent agent_ucs_bladecenter (separator is <TAB> and means tabulator):
#
# <<<ucs_c_rack_server_motherboard_power:sep(9)>>>
# computeMbPowerStats<TAB>dn sys/rack-unit-1/board/power-stats<TAB>consumedPower 88<TAB>inputCurrent 6.00<TAB>inputVoltage 12.100
# computeMbPowerStats<TAB>dn sys/rack-unit-2/board/power-stats<TAB>consumedPower 88<TAB>inputCurrent 6.00<TAB>inputVoltage 12.100

# Default values for consumed power selected according to exemplary monitored real world values
# of a rack servers motherboards. Reasonable values for the actual use case depend on the rack
# servers configuration (racks used in rack server) and require customization via WATO rule.


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition

check_info = {}


def parse_ucs_c_rack_server_power(string_table):
    """
    Returns dict with indexed rack motherboards mapped to keys and consumed power,
    input current status and input voltage status as value.
    """
    parsed = {}
    # The element count of string_table lines is under our control (agent output) and
    # ensured to have expected length. It is ensured that elements contain a
    # string. Handles invalid values provided by the XML API which cannot be
    # casted by setting corresponding values to None.
    for _, dn, power, current, voltage in string_table:
        motherboard = (
            dn.replace("dn ", "")
            .replace("sys/", "")
            .replace("rack-unit-", "Rack Unit ")
            .replace("/board", "")
            .replace("/power-stats", "")
        )
        parsed.setdefault(motherboard, {})
        for ds_key, ds, cast_function in (
            ("consumedPower", power, float),  # consumedPower is no longer int but float instead!!
            ("inputCurrent", current, float),
            ("inputVoltage", voltage, float),
        ):
            try:
                # Power values are of type int. Current and voltage values are of type float but
                # converted to int. Hogher accuracy of float is not required.
                parsed[motherboard][ds_key] = cast_function(ds.replace(ds_key + " ", ""))
            except ValueError:
                # The default value set by setdefault is None. These values are handled in the
                # check function appropriatelly.
                pass
    return parsed


def check_ucs_c_rack_server_power(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    yield check_levels(
        data["consumedPower"], "power", params["power_upper_levels"], unit="W", infoname="Power"
    )
    yield 0, "Current: %s A" % data["inputCurrent"]
    yield 0, "Voltage: %s V" % data["inputVoltage"]


def discover_ucs_c_rack_server_power(section):
    yield from ((item, {}) for item in section)


check_info["ucs_c_rack_server_power"] = LegacyCheckDefinition(
    name="ucs_c_rack_server_power",
    parse_function=parse_ucs_c_rack_server_power,
    service_name="Motherboard Power Statistics %s",
    discovery_function=discover_ucs_c_rack_server_power,
    check_function=check_ucs_c_rack_server_power,
    check_ruleset_name="power_multiitem",
    check_default_parameters={
        "power_upper_levels": (90, 100),
    },
)
