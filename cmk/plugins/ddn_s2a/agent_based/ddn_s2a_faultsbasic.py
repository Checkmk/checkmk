#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer until we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.ddn_s2a.lib import parse_ddn_s2a_api_response

#   .--Parse function------------------------------------------------------.
#   |  ____                        __                  _   _               |
#   | |  _ \ __ _ _ __ ___  ___   / _|_   _ _ __   ___| |_(_) ___  _ __    |
#   | | |_) / _` | '__/ __|/ _ \ | |_| | | | '_ \ / __| __| |/ _ \| '_ \   |
#   | |  __/ (_| | |  \__ \  __/ |  _| |_| | | | | (__| |_| | (_) | | | |  |
#   | |_|   \__,_|_|  |___/\___| |_|  \__,_|_| |_|\___|\__|_|\___/|_| |_|  |
#   |                                                                      |
#   '----------------------------------------------------------------------'

_NON_UNIQUE_KEYS = (
    "failed_avr_fan_ctrl_item",
    "failed_avr_pwr_sup_item",
    "failed_avr_temp_W_item",
    "failed_avr_temp_C_item",
    "failed_disk_item",
)


@dataclass(frozen=True, kw_only=True)
class Section:
    values: Mapping[str, str]
    """Unique values, keyed by their API field name."""
    failed_items: Mapping[str, Sequence[str]]
    """Names of the failed components, keyed by their API field name."""


def parse_ddn_s2a_faultsbasic(string_table: StringTable) -> Section:
    parsed = parse_ddn_s2a_api_response(string_table)
    return Section(
        values={key: value[0] for key, value in parsed.items() if key not in _NON_UNIQUE_KEYS},
        failed_items={key: value for key, value in parsed.items() if key in _NON_UNIQUE_KEYS},
    )


agent_section_ddn_s2a_faultsbasic = AgentSection(
    name="ddn_s2a_faultsbasic",
    parse_function=parse_ddn_s2a_faultsbasic,
)


# .
#   .--Disks---------------------------------------------------------------.
#   |                        ____  _     _                                 |
#   |                       |  _ \(_)___| | _____                          |
#   |                       | | | | / __| |/ / __|                         |
#   |                       | |_| | \__ \   <\__ \                         |
#   |                       |____/|_|___/_|\_\___/                         |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_ddn_s2a_faultsbasic_disks(section: Section) -> DiscoveryResult:
    if "disk_failures_count" in section.values:
        yield Service()


def check_ddn_s2a_faultsbasic_disks(params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from check_levels(
        int(section.values["disk_failures_count"]),
        None,
        params["levels"],
        human_readable_func=str,
        infoname="Failures detected",
    )

    if failed_disks := section.failed_items.get("failed_disk_item"):
        yield Result(state=State.OK, summary="Failed disks: " + ", ".join(failed_disks))


check_plugin_ddn_s2a_faultsbasic_disks = CheckPlugin(
    name="ddn_s2a_faultsbasic_disks",
    service_name="DDN S2A Disks",
    sections=["ddn_s2a_faultsbasic"],
    discovery_function=discover_ddn_s2a_faultsbasic_disks,
    check_function=check_ddn_s2a_faultsbasic_disks,
    check_ruleset_name="disk_failures",
    check_default_parameters={
        "levels": (1, 2),
    },
)

# .
#   .--Temperature---------------------------------------------------------.
#   |     _____                                   _                        |
#   |    |_   _|__ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |      | |/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |      | |  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      |_|\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   '----------------------------------------------------------------------'


def discover_ddn_s2a_faultsbasic_temp(section: Section) -> DiscoveryResult:
    if "avr_temp_W_failures_count" in section.values:
        yield Service()


def check_ddn_s2a_faultsbasic_temp(section: Section) -> CheckResult:
    crit_failures = int(section.values["avr_temp_C_failures_count"])
    warn_failures = int(section.values["avr_temp_W_failures_count"])

    if crit_failures:
        state = State.CRIT
    elif warn_failures:
        state = State.WARN
    else:
        state = State.OK

    summary = f"{crit_failures} critical failures, {warn_failures} warnings"
    if crit_failures_items := section.failed_items.get("failed_avr_temp_C_item"):
        summary += ". Critical failures: " + ", ".join(crit_failures_items)
    if warn_failures_items := section.failed_items.get("failed_avr_temp_W_item"):
        summary += ". Warnings: " + ", ".join(warn_failures_items)

    yield Result(state=state, summary=summary)


check_plugin_ddn_s2a_faultsbasic_temp = CheckPlugin(
    name="ddn_s2a_faultsbasic_temp",
    service_name="DDN S2A Temperature",
    sections=["ddn_s2a_faultsbasic"],
    discovery_function=discover_ddn_s2a_faultsbasic_temp,
    check_function=check_ddn_s2a_faultsbasic_temp,
)

# .
#   .--Power supplies------------------------------------------------------.
#   |  ____                                                _ _             |
#   | |  _ \ _____      _____ _ __   ___ _   _ _ __  _ __ | (_) ___  ___   |
#   | | |_) / _ \ \ /\ / / _ \ '__| / __| | | | '_ \| '_ \| | |/ _ \/ __|  |
#   | |  __/ (_) \ V  V /  __/ |    \__ \ |_| | |_) | |_) | | |  __/\__ \  |
#   | |_|   \___/ \_/\_/ \___|_|    |___/\__,_| .__/| .__/|_|_|\___||___/  |
#   |                                         |_|   |_|                    |
#   '----------------------------------------------------------------------'


def discover_ddn_s2a_faultsbasic_ps(section: Section) -> DiscoveryResult:
    if "avr_pwr_sup_failures_count" in section.values:
        yield Service()


def check_ddn_s2a_faultsbasic_ps(section: Section) -> CheckResult:
    if int(section.values["avr_pwr_sup_failures_count"]) > 0:
        yield Result(
            state=State.CRIT,
            summary="Power supply failure: "
            + ", ".join(section.failed_items["failed_avr_pwr_sup_item"]),
        )
    else:
        yield Result(state=State.OK, summary="No power supply failures detected")


check_plugin_ddn_s2a_faultsbasic_ps = CheckPlugin(
    name="ddn_s2a_faultsbasic_ps",
    service_name="DDN S2A Power Supplies",
    sections=["ddn_s2a_faultsbasic"],
    discovery_function=discover_ddn_s2a_faultsbasic_ps,
    check_function=check_ddn_s2a_faultsbasic_ps,
)

# .
#   .--Fans----------------------------------------------------------------.
#   |                         _____                                        |
#   |                        |  ___|_ _ _ __  ___                          |
#   |                        | |_ / _` | '_ \/ __|                         |
#   |                        |  _| (_| | | | \__ \                         |
#   |                        |_|  \__,_|_| |_|___/                         |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_ddn_s2a_faultsbasic_fans(section: Section) -> DiscoveryResult:
    if "avr_fan_ctrl_failures_count" in section.values:
        yield Service()


def check_ddn_s2a_faultsbasic_fans(params: Mapping[str, Any], section: Section) -> CheckResult:
    fan_failures = int(section.values["avr_fan_ctrl_failures_count"])

    yield from check_levels(
        fan_failures,
        None,
        params["levels"],
        human_readable_func=str,
        infoname="Detected fan failures",
    )

    if fan_failures:
        yield from (
            Result(state=State.OK, summary=txt)
            for txt in section.failed_items["failed_avr_fan_ctrl_item"]
        )


check_plugin_ddn_s2a_faultsbasic_fans = CheckPlugin(
    name="ddn_s2a_faultsbasic_fans",
    service_name="DDN S2A Fans",
    sections=["ddn_s2a_faultsbasic"],
    discovery_function=discover_ddn_s2a_faultsbasic_fans,
    check_function=check_ddn_s2a_faultsbasic_fans,
    check_ruleset_name="fan_failures",
    check_default_parameters={"levels": (1, 2)},
)

# .
#   .--Ping fault----------------------------------------------------------.
#   |             ____  _                __             _ _                |
#   |            |  _ \(_)_ __   __ _   / _| __ _ _   _| | |_              |
#   |            | |_) | | '_ \ / _` | | |_ / _` | | | | | __|             |
#   |            |  __/| | | | | (_| | |  _| (_| | |_| | | |_              |
#   |            |_|   |_|_| |_|\__, | |_|  \__,_|\__,_|_|\__|             |
#   |                           |___/                                      |
#   '----------------------------------------------------------------------'


def discover_ddn_s2a_faultsbasic_pingfault(section: Section) -> DiscoveryResult:
    if "ping_fault" in section.values:
        yield Service()


def check_ddn_s2a_faultsbasic_pingfault(section: Section) -> CheckResult:
    if section.values["ping_fault"] == "FALSE":
        yield Result(state=State.OK, summary="No fault detected")
    elif "ping_fault_tag" in section.values:
        yield Result(state=State.WARN, summary="Ping Fault: " + section.values["ping_fault_tag"])
    elif section.values["ping_fault"] == "TRUE":
        yield Result(state=State.WARN, summary="Ping Fault")


check_plugin_ddn_s2a_faultsbasic_pingfault = CheckPlugin(
    name="ddn_s2a_faultsbasic_pingfault",
    service_name="DDN S2A Ping Fault Status",
    sections=["ddn_s2a_faultsbasic"],
    discovery_function=discover_ddn_s2a_faultsbasic_pingfault,
    check_function=check_ddn_s2a_faultsbasic_pingfault,
)

# .
#   .--Boot status---------------------------------------------------------.
#   |         ____              _         _        _                       |
#   |        | __ )  ___   ___ | |_   ___| |_ __ _| |_ _   _ ___           |
#   |        |  _ \ / _ \ / _ \| __| / __| __/ _` | __| | | / __|          |
#   |        | |_) | (_) | (_) | |_  \__ \ || (_| | |_| |_| \__ \          |
#   |        |____/ \___/ \___/ \__| |___/\__\__,_|\__|\__,_|___/          |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_ddn_s2a_faultsbasic_bootstatus(section: Section) -> DiscoveryResult:
    if "system_fully_booted" in section.values:
        yield Service()


def check_ddn_s2a_faultsbasic_bootstatus(section: Section) -> CheckResult:
    if section.values["system_fully_booted"] == "TRUE":
        yield Result(state=State.OK, summary="System fully booted")
    else:
        yield Result(state=State.WARN, summary="System not fully booted")


check_plugin_ddn_s2a_faultsbasic_bootstatus = CheckPlugin(
    name="ddn_s2a_faultsbasic_bootstatus",
    service_name="DDN S2A Boot Status",
    sections=["ddn_s2a_faultsbasic"],
    discovery_function=discover_ddn_s2a_faultsbasic_bootstatus,
    check_function=check_ddn_s2a_faultsbasic_bootstatus,
)

# .
#   .--Cache coherency-----------------------------------------------------.
#   |                      ____           _                                |
#   |                     / ___|__ _  ___| |__   ___                       |
#   |                    | |   / _` |/ __| '_ \ / _ \                      |
#   |                    | |__| (_| | (__| | | |  __/                      |
#   |                     \____\__,_|\___|_| |_|\___|                      |
#   |                                                                      |
#   |                     _                                                |
#   |            ___ ___ | |__   ___ _ __ ___ _ __   ___ _   _             |
#   |           / __/ _ \| '_ \ / _ \ '__/ _ \ '_ \ / __| | | |            |
#   |          | (_| (_) | | | |  __/ | |  __/ | | | (__| |_| |            |
#   |           \___\___/|_| |_|\___|_|  \___|_| |_|\___|\__, |            |
#   |                                                    |___/             |
#   '----------------------------------------------------------------------'

_CACHE_COHERENCY_STATES = {
    "established": State.OK,
    "not enabled": State.WARN,
    "not established": State.CRIT,
}


def discover_ddn_s2a_faultsbasic_cachecoh(section: Section) -> DiscoveryResult:
    if "hstd1_online_failure" in section.values:
        yield Service()


def check_ddn_s2a_faultsbasic_cachecoh(section: Section) -> CheckResult:
    if not (cache_coherency := section.values.get("cache_coherency")):
        # The value is only supplied in case of a failure. A missing value is an implicit OK
        # according to the API documentation.
        yield Result(state=State.OK, summary="Cache coherency: established")
        return

    yield Result(
        state=_CACHE_COHERENCY_STATES.get(cache_coherency, State.UNKNOWN),
        summary="Cache coherency: " + cache_coherency,
    )


check_plugin_ddn_s2a_faultsbasic_cachecoh = CheckPlugin(
    name="ddn_s2a_faultsbasic_cachecoh",
    service_name="DDN S2A Cache Coherency",
    sections=["ddn_s2a_faultsbasic"],
    discovery_function=discover_ddn_s2a_faultsbasic_cachecoh,
    check_function=check_ddn_s2a_faultsbasic_cachecoh,
)

# .
#   .--Dual communication--------------------------------------------------.
#   |         ____              _                                          |
#   |        |  _ \ _   _  __ _| |   ___ ___  _ __ ___  _ __ ___           |
#   |        | | | | | | |/ _` | |  / __/ _ \| '_ ` _ \| '_ ` _ \          |
#   |        | |_| | |_| | (_| | | | (_| (_) | | | | | | | | | | |         |
#   |        |____/ \__,_|\__,_|_|  \___\___/|_| |_| |_|_| |_| |_|         |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_ddn_s2a_faultsbasic_dualcomm(section: Section) -> DiscoveryResult:
    if "hstd1_online_failure" in section.values:
        yield Service()


def check_ddn_s2a_faultsbasic_dualcomm(section: Section) -> CheckResult:
    dual_comm_established = section.values.get("dual_comm_established")

    # This value is only transmitted by the API in case of a failure.
    # Therefore, a non-existant value is an implicit "TRUE" here.
    if dual_comm_established in ("TRUE", None):
        yield Result(state=State.OK, summary="Dual comm established")
    elif dual_comm_established == "FALSE":
        yield Result(state=State.CRIT, summary="Dual comm not established")


check_plugin_ddn_s2a_faultsbasic_dualcomm = CheckPlugin(
    name="ddn_s2a_faultsbasic_dualcomm",
    service_name="DDN S2A Dual Communication",
    sections=["ddn_s2a_faultsbasic"],
    discovery_function=discover_ddn_s2a_faultsbasic_dualcomm,
    check_function=check_ddn_s2a_faultsbasic_dualcomm,
)

# .
#   .--Ethernet------------------------------------------------------------.
#   |              _____ _   _                          _                  |
#   |             | ____| |_| |__   ___ _ __ _ __   ___| |_                |
#   |             |  _| | __| '_ \ / _ \ '__| '_ \ / _ \ __|               |
#   |             | |___| |_| | | |  __/ |  | | | |  __/ |_                |
#   |             |_____|\__|_| |_|\___|_|  |_| |_|\___|\__|               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_ddn_s2a_faultsbasic_ethernet(section: Section) -> DiscoveryResult:
    if "hstd1_online_failure" in section.values:
        yield Service()


def check_ddn_s2a_faultsbasic_ethernet(section: Section) -> CheckResult:
    ethernet_working = section.values.get("ethernet_working")

    # This value is only transmitted by the API in case of a failure.
    # Therefore, a non-existant value is an implicit "established" here.
    if ethernet_working in ("established", None):
        yield Result(state=State.OK, summary="Ethernet connection established")
    else:
        yield Result(state=State.WARN, summary=f"Ethernet {ethernet_working}")


check_plugin_ddn_s2a_faultsbasic_ethernet = CheckPlugin(
    name="ddn_s2a_faultsbasic_ethernet",
    service_name="DDN S2A Ethernet",
    sections=["ddn_s2a_faultsbasic"],
    discovery_function=discover_ddn_s2a_faultsbasic_ethernet,
    check_function=check_ddn_s2a_faultsbasic_ethernet,
)

# .
#   .--Unit status---------------------------------------------------------.
#   |           _   _       _ _         _        _                         |
#   |          | | | |_ __ (_) |_   ___| |_ __ _| |_ _   _ ___             |
#   |          | | | | '_ \| | __| / __| __/ _` | __| | | / __|            |
#   |          | |_| | | | | | |_  \__ \ || (_| | |_| |_| \__ \            |
#   |           \___/|_| |_|_|\__| |___/\__\__,_|\__|\__,_|___/            |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_ddn_s2a_faultsbasic(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=index)
        for index in ("1", "2")
        if f"hstd{index}_online_failure" in section.values
    )


def check_ddn_s2a_faultsbasic(item: str, section: Section) -> CheckResult:
    if (online_failure := section.values.get(f"hstd{item}_online_failure")) is None:
        return
    online_status = section.values.get(f"hstd{item}_online_status", "")

    if online_failure == "TRUE":
        if online_status.lower() in ("restarting", "not installed"):
            yield Result(state=State.WARN, summary=f"Unit {online_status}")
        else:
            yield Result(
                state=State.CRIT, summary=f"Failure detected - Online status: {online_status}"
            )
    elif online_failure == "FALSE":
        yield Result(state=State.OK, summary="No failure detected")


check_plugin_ddn_s2a_faultsbasic = CheckPlugin(
    name="ddn_s2a_faultsbasic",
    service_name="DDN S2A Unit %s",
    discovery_function=discover_ddn_s2a_faultsbasic,
    check_function=check_ddn_s2a_faultsbasic,
)
