#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.base.check_legacy_includes.ddn_s2a import parse_ddn_s2a_api_response

check_info = {}

#   .--Parse function------------------------------------------------------.
#   |  ____                        __                  _   _               |
#   | |  _ \ __ _ _ __ ___  ___   / _|_   _ _ __   ___| |_(_) ___  _ __    |
#   | | |_) / _` | '__/ __|/ _ \ | |_| | | | '_ \ / __| __| |/ _ \| '_ \   |
#   | |  __/ (_| | |  \__ \  __/ |  _| |_| | | | | (__| |_| | (_) | | | |  |
#   | |_|   \__,_|_|  |___/\___| |_|  \__,_|_| |_|\___|\__|_|\___/|_| |_|  |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def parse_ddn_s2a_faultsbasic(string_table):
    non_unique_keys = [
        "failed_avr_fan_ctrl_item",
        "failed_avr_pwr_sup_item",
        "failed_avr_temp_W_item",
        "failed_avr_temp_C_item",
        "failed_disk_item",
    ]
    return {
        key: value if key in non_unique_keys else value[0]
        for key, value in parse_ddn_s2a_api_response(string_table).items()
    }


# .
#   .--Disks---------------------------------------------------------------.
#   |                        ____  _     _                                 |
#   |                       |  _ \(_)___| | _____                          |
#   |                       | | | | / __| |/ / __|                         |
#   |                       | |_| | \__ \   <\__ \                         |
#   |                       |____/|_|___/_|\_\___/                         |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_ddn_s2a_faultsbasic_disks(parsed):
    if "disk_failures_count" in parsed:
        yield None, {}


def check_ddn_s2a_faultsbasic_disks(_no_item, params, parsed):
    yield check_levels(
        int(parsed["disk_failures_count"]),
        None,
        params["levels"],
        human_readable_func=str,
        infoname="Failures detected",
    )

    if parsed.get("failed_disk_item"):
        yield 0, "Failed disks: " + ", ".join(parsed["failed_disk_item"])


check_info["ddn_s2a_faultsbasic.disks"] = LegacyCheckDefinition(
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


def discover_ddn_s2a_faultsbasic_temp(parsed):
    if "avr_temp_W_failures_count" in parsed:
        return [(None, None)]
    return []


def check_ddn_s2a_faultsbasic_temp(_no_item, _no_params, parsed):
    crit_failures = int(parsed["avr_temp_C_failures_count"])
    warn_failures = int(parsed["avr_temp_W_failures_count"])

    if crit_failures:
        status = 2
    elif warn_failures:
        status = 1
    else:
        status = 0

    infotext = "%d critical failures, %d warnings" % (crit_failures, warn_failures)

    crit_failures_items = parsed.get("failed_avr_temp_C_item")
    if crit_failures_items:
        infotext += ". Critical failures: " + ", ".join(crit_failures_items)

    warn_failures_items = parsed.get("failed_avr_temp_W_item")
    if warn_failures_items:
        infotext += ". Warnings: " + ", ".join(warn_failures_items)

    return status, infotext


check_info["ddn_s2a_faultsbasic.temp"] = LegacyCheckDefinition(
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


def discover_ddn_s2a_faultsbasic_ps(parsed):
    if "avr_pwr_sup_failures_count" in parsed:
        return [(None, None)]
    return []


def check_ddn_s2a_faultsbasic_ps(_no_item, _no_params, parsed):
    ps_failures = int(parsed["avr_pwr_sup_failures_count"])
    if ps_failures > 0:
        infotext = "Power supply failure: "
        infotext += ", ".join(parsed["failed_avr_pwr_sup_item"])
        return 2, infotext
    return 0, "No power supply failures detected"


check_info["ddn_s2a_faultsbasic.ps"] = LegacyCheckDefinition(
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


def discover_ddn_s2a_faultsbasic_fans(parsed):
    if "avr_fan_ctrl_failures_count" in parsed:
        yield None, {}


def check_ddn_s2a_faultsbasic_fans(_no_item, params, parsed):
    fan_failures = int(parsed["avr_fan_ctrl_failures_count"])

    yield check_levels(
        fan_failures,
        None,
        params["levels"],
        human_readable_func=str,
        infoname="Detected fan failures",
    )

    if fan_failures:
        yield from ((0, txt) for txt in parsed["failed_avr_fan_ctrl_item"])


check_info["ddn_s2a_faultsbasic.fans"] = LegacyCheckDefinition(
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


def discover_ddn_s2a_faultsbasic_pingfault(parsed):
    if "ping_fault" in parsed:
        return [(None, None)]
    return []


def check_ddn_s2a_faultsbasic_pingfault(_no_item, _no_params, parsed):
    if parsed["ping_fault"] == "FALSE":
        return 0, "No fault detected"
    if "ping_fault_tag" in parsed:
        return 1, "Ping Fault: " + parsed["ping_fault_tag"]
    if parsed["ping_fault"] == "TRUE":
        return 1, "Ping Fault"
    return None


check_info["ddn_s2a_faultsbasic.pingfault"] = LegacyCheckDefinition(
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


def discover_ddn_s2a_faultsbasic_bootstatus(parsed):
    if "system_fully_booted" in parsed:
        return [(None, None)]
    return []


def check_ddn_s2a_faultsbasic_bootstatus(_no_item, _no_params, parsed):
    if parsed["system_fully_booted"] == "TRUE":
        return 0, "System fully booted"
    return 1, "System not fully booted"


check_info["ddn_s2a_faultsbasic.bootstatus"] = LegacyCheckDefinition(
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


def discover_ddn_s2a_faultsbasic_cachecoh(parsed):
    if "hstd1_online_failure" in parsed:
        return [(None, None)]
    return []


def check_ddn_s2a_faultsbasic_cachecoh(_no_item, _no_params, parsed):
    cache_coherency = parsed.get("cache_coherency")
    if cache_coherency:
        cache_coherency_states = {
            "established": 0,
            "not enabled": 1,
            "not established": 2,
        }

        return cache_coherency_states.get(cache_coherency, 3), "Cache coherency: " + cache_coherency

    # The value is only supplied in case of a failure. A missing value is an implicit OK
    # according to the API documentation.
    return 0, "Cache coherency: established"


check_info["ddn_s2a_faultsbasic.cachecoh"] = LegacyCheckDefinition(
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


def discover_ddn_s2a_faultsbasic_dualcomm(parsed):
    if "hstd1_online_failure" in parsed:
        return [(None, None)]
    return []


def check_ddn_s2a_faultsbasic_dualcomm(_no_item, _no_params, parsed):
    dual_comm_established = parsed.get("dual_comm_established")

    # This value is only transmitted by the API in case of a failure.
    # Therefore, a non-existant value is an implicit "TRUE" here.
    if dual_comm_established == "TRUE" or dual_comm_established is None:
        return 0, "Dual comm established"
    if dual_comm_established == "FALSE":
        return 2, "Dual comm not established"
    return None


check_info["ddn_s2a_faultsbasic.dualcomm"] = LegacyCheckDefinition(
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


def discover_ddn_s2a_faultsbasic_ethernet(parsed):
    if "hstd1_online_failure" in parsed:
        return [(None, None)]
    return []


def check_ddn_s2a_faultsbasic_ethernet(_no_item, _no_params, parsed):
    ethernet_working = parsed.get("ethernet_working")

    # This value is only transmitted by the API in case of a failure.
    # Therefore, a non-existant value is an implicit "established" here.
    if ethernet_working == "established" or ethernet_working is None:
        yield 0, "Ethernet connection established"
    else:
        yield 1, "Ethernet " + ethernet_working


check_info["ddn_s2a_faultsbasic.ethernet"] = LegacyCheckDefinition(
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


def discover_ddn_s2a_faultsbasic(parsed):
    for index in ["1", "2"]:
        if "hstd%s_online_failure" % index in parsed:
            yield index, None


def check_ddn_s2a_faultsbasic(item, _no_params, parsed):
    online_failure = parsed["hstd%s_online_failure" % item]
    online_status = parsed.get("hstd%s_online_status" % item, "")

    if online_failure == "TRUE":
        if online_status.lower() in ["restarting", "not installed"]:
            yield 1, "Unit " + online_status
        else:
            yield 2, "Failure detected - Online status: " + online_status
    elif online_failure == "FALSE":
        yield 0, "No failure detected"


check_info["ddn_s2a_faultsbasic"] = LegacyCheckDefinition(
    name="ddn_s2a_faultsbasic",
    parse_function=parse_ddn_s2a_faultsbasic,
    service_name="DDN S2A Unit %s",
    discovery_function=discover_ddn_s2a_faultsbasic,
    check_function=check_ddn_s2a_faultsbasic,
)
