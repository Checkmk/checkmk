#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .
#   .--Status--------------------------------------------------------------.
#   |                    ____  _        _                                  |
#   |                   / ___|| |_ __ _| |_ _   _ ___                      |
#   |                   \___ \| __/ _` | __| | | / __|                     |
#   |                    ___) | || (_| | |_| |_| \__ \                     |
#   |                   |____/ \__\__,_|\__|\__,_|___/                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.conversion import (
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    exists,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)


def discover_entersekt(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_entersekt_status(section: StringTable) -> CheckResult:
    if section[0][0] == "true":
        yield Result(state=State.OK, summary="Server is running")
    else:
        yield Result(state=State.CRIT, summary="Server is NOT running")


def parse_entersekt(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_entersekt = SimpleSNMPSection(
    name="entersekt",
    detect=all_of(contains(".1.3.6.1.2.1.1.1.0", "linux"), exists(".1.3.6.1.4.1.38235.2.3.1.0")),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.38235.2",
        oids=["3.1.0", "3.4.0", "3.8.0", "3.9.0", "17.1.0"],
    ),
    parse_function=parse_entersekt,
)


check_plugin_entersekt = CheckPlugin(
    name="entersekt",
    service_name="Entersekt Server Status",
    discovery_function=discover_entersekt,
    check_function=check_entersekt_status,
)


# .
#   .--Http EmrErrors------------------------------------------------------.
#   |                         _   _ _   _                                  |
#   |                        | | | | |_| |_ _ __                           |
#   |                        | |_| | __| __| '_ \                          |
#   |                        |  _  | |_| |_| |_) |                         |
#   |                        |_| |_|\__|\__| .__/                          |
#   |                                      |_|                             |
#   |         _____                _____                                   |
#   |        | ____|_ __ ___  _ __| ____|_ __ _ __ ___  _ __ ___           |
#   |        |  _| | '_ ` _ \| '__|  _| | '__| '__/ _ \| '__/ __|          |
#   |        | |___| | | | | | |  | |___| |  | | | (_) | |  \__ \          |
#   |        |_____|_| |_| |_|_|  |_____|_|  |_|  \___/|_|  |___/          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'
def discover_entersekt_emrerrors(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_entersekt_emrerrors(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    if params:
        (warn, crit) = params["levels"]
    else:
        (warn, crit) = (100, 200)
    errors = int(section[0][1])
    if errors > crit:
        yield Result(
            state=State.CRIT, summary=f"Number of errors is {errors} which is higher than {crit}"
        )
    elif errors > warn:
        yield Result(
            state=State.WARN, summary=f"Number of errors is {errors} which is higher than {warn}"
        )
    else:
        yield Result(state=State.OK, summary=f"Number of errors is {errors}")
    yield Metric("Errors", errors, levels=(warn, crit))


check_plugin_entersekt_emrerrors = CheckPlugin(
    name="entersekt_emrerrors",
    service_name="Entersekt http EMR Errors",
    sections=["entersekt"],
    discovery_function=discover_entersekt_emrerrors,
    check_function=check_entersekt_emrerrors,
    check_ruleset_name="entersekt_emrerrors",
    check_default_parameters={},
)

# .
#   .--sgHttp EcertErrors--------------------------------------------------.
#   |                              _   _ _   _                             |
#   |                    ___  __ _| | | | |_| |_ _ __                      |
#   |                   / __|/ _` | |_| | __| __| '_ \                     |
#   |                   \__ \ (_| |  _  | |_| |_| |_) |                    |
#   |                   |___/\__, |_| |_|\__|\__| .__/                     |
#   |                        |___/              |_|                        |
#   |        _____              _   _____                                  |
#   |       | ____|___ ___ _ __| |_| ____|_ __ _ __ ___  _ __ ___          |
#   |       |  _| / __/ _ \ '__| __|  _| | '__| '__/ _ \| '__/ __|         |
#   |       | |__| (_|  __/ |  | |_| |___| |  | | | (_) | |  \__ \         |
#   |       |_____\___\___|_|   \__|_____|_|  |_|  \___/|_|  |___/         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_entersekt_ecerterrors(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_entersekt_ecerterrors(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    if params:
        (warn, crit) = params["levels"]
    else:
        (warn, crit) = (100, 200)
    errors = int(section[0][2])
    if errors > crit:
        yield Result(
            state=State.CRIT, summary=f"Number of errors is {errors} which is higher than {crit}"
        )
    elif errors > warn:
        yield Result(
            state=State.WARN, summary=f"Number of errors is {errors} which is higher than {warn}"
        )
    else:
        yield Result(state=State.OK, summary=f"Number of errors is {errors}")
    yield Metric("Errors", errors, levels=(warn, crit))


check_plugin_entersekt_ecerterrors = CheckPlugin(
    name="entersekt_ecerterrors",
    service_name="Entersekt http Ecert Errors",
    sections=["entersekt"],
    discovery_function=discover_entersekt_ecerterrors,
    check_function=check_entersekt_ecerterrors,
    check_ruleset_name="entersekt_ecerterrors",
    check_default_parameters={},
)


# .
#   .--Soap Service Errors-------------------------------------------------.
#   |     ____                      ____                  _                |
#   |    / ___|  ___   __ _ _ __   / ___|  ___ _ ____   _(_) ___ ___       |
#   |    \___ \ / _ \ / _` | '_ \  \___ \ / _ \ '__\ \ / / |/ __/ _ \      |
#   |     ___) | (_) | (_| | |_) |  ___) |  __/ |   \ V /| | (_|  __/      |
#   |    |____/ \___/ \__,_| .__/  |____/ \___|_|    \_/ |_|\___\___|      |
#   |                      |_|                                             |
#   |                    _____                                             |
#   |                   | ____|_ __ _ __ ___  _ __ ___                     |
#   |                   |  _| | '__| '__/ _ \| '__/ __|                    |
#   |                   | |___| |  | | | (_) | |  \__ \                    |
#   |                   |_____|_|  |_|  \___/|_|  |___/                    |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'
def discover_entersekt_soaperrors(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_entersekt_soaperrors(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    yield from check_levels(
        value=int(section[0][3]),
        dsname="Errors",
        params=params["levels"],
        human_readable_func=str,
        infoname="Number of errors",
    )


check_plugin_entersekt_soaperrors = CheckPlugin(
    name="entersekt_soaperrors",
    service_name="Entersekt Soap Service Errors",
    sections=["entersekt"],
    discovery_function=discover_entersekt_soaperrors,
    check_function=check_entersekt_soaperrors,
    check_ruleset_name="entersekt_soaperrors",
    check_default_parameters={},
)

# .
#   .--sgConsoleDaysToNextCertExpiry---------------------------------------.
#   |             ____                      _      ____                    |
#   |  ___  __ _ / ___|___  _ __  ___  ___ | | ___|  _ \  __ _ _   _ ___   |
#   | / __|/ _` | |   / _ \| '_ \/ __|/ _ \| |/ _ \ | | |/ _` | | | / __|  |
#   | \__ \ (_| | |__| (_) | | | \__ \ (_) | |  __/ |_| | (_| | |_| \__ \  |
#   | |___/\__, |\____\___/|_| |_|___/\___/|_|\___|____/ \__,_|\__, |___/  |
#   |      |___/                                               |___/       |
#   |  _____     _   _           _    ____          _   _____              |
#   | |_   _|__ | \ | | _____  _| |_ / ___|___ _ __| |_| ____|_  ___ __    |
#   |   | |/ _ \|  \| |/ _ \ \/ / __| |   / _ \ '__| __|  _| \ \/ / '_ \   |
#   |   | | (_) | |\  |  __/>  <| |_| |__|  __/ |  | |_| |___ >  <| |_) |  |
#   |   |_|\___/|_| \_|\___/_/\_\\__|\____\___|_|   \__|_____/_/\_\ .__/   |
#   |                                                             |_|      |
#   |                            _                                         |
#   |                           (_)_ __ _   _                              |
#   |                           | | '__| | | |                             |
#   |                           | | |  | |_| |                             |
#   |                           |_|_|   \__, |                             |
#   |                                   |___/                              |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_entersekt_certexpiry(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_entersekt_certexpiry(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    if params:
        (warn, crit) = params["levels"]
    else:
        (warn, crit) = (20, 10)
    days = int(section[0][4])
    if days < crit:
        yield Result(
            state=State.CRIT,
            summary=f"Number of days until expiration is {days} which is less than {crit}",
        )
    elif days < warn:
        yield Result(
            state=State.WARN,
            summary=f"Number of days until expiration is {days} which is less than {warn}",
        )
    else:
        yield Result(state=State.OK, summary=f"Number of days is {days}")
    yield Metric("Days", days, levels=(warn, crit))


check_plugin_entersekt_certexpiry = CheckPlugin(
    name="entersekt_certexpiry",
    service_name="Entersekt Certificate Expiration",
    sections=["entersekt"],
    discovery_function=discover_entersekt_certexpiry,
    check_function=check_entersekt_certexpiry,
    check_ruleset_name="entersekt_certexpiry",
    check_default_parameters={},
)
