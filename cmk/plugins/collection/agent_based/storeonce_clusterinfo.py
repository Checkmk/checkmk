#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

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
from cmk.plugins.lib import df, storeonce, uptime

Section = Mapping[str, str]

# example output:
#
# <<<storeonce_clusterinfo:sep(9)>>>
# Appliance Name  HPCT15732RTD
# Network Name    10.0.0.240
# Serial Number   CT15732RTD
# Software Version        3.15.1-1636.1
# Product Class   HPE StoreOnce 4700 Backup
# Total Capacity  75952.808613643
# Free Space      53819.324528395
# User Data Stored        305835.97014174
# Size On Disk    19180.587585836
# Total Capacity (bytes)  75952808613643
# Free Space (bytes)      53819324528395
# User Data Stored (bytes)        305835970141743
# Size On Disk (bytes)    19180587585836
# Dedupe Ratio    15.945078260667367
# Cluster Health Level    1
# Cluster Health  OK
# Cluster Status  Running
# Replication Health Level        1
# Replication Health      OK
# Replication Status      Running
# Uptime Seconds  4305030
# sysContact      None
# sysLocation     None
# isMixedCluster  false


def parse_storeonce_clusterinfo(string_table: StringTable) -> Section:
    return {key: value for key, value, *_rest in string_table}


agent_section_storeonce_clusterinfo = AgentSection(
    name="storeonce_clusterinfo",
    parse_function=parse_storeonce_clusterinfo,
)

# .
#   .--general-------------------------------------------------------------.
#   |                                                  _                   |
#   |                   __ _  ___ _ __   ___ _ __ __ _| |                  |
#   |                  / _` |/ _ \ '_ \ / _ \ '__/ _` | |                  |
#   |                 | (_| |  __/ | | |  __/ | | (_| | |                  |
#   |                  \__, |\___|_| |_|\___|_|  \__,_|_|                  |
#   |                  |___/                                               |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_storeonce_clusterinfo(section: Section) -> DiscoveryResult:
    if "Product Class" in section:
        yield Service(item=section["Product Class"])


# this seems to be a HaSI plugin
def check_storeonce_clusterinfo(item: str, section: Section) -> CheckResult:
    yield Result(state=State.OK, summary=f"Name: {section['Appliance Name']}")
    yield Result(state=State.OK, summary=f"Serial Number: {section['Serial Number']}")
    yield Result(state=State.OK, summary=f"Version: {section['Software Version']}")


check_plugin_storeonce_clusterinfo = CheckPlugin(
    name="storeonce_clusterinfo",
    service_name="%s",
    discovery_function=discover_storeonce_clusterinfo,
    check_function=check_storeonce_clusterinfo,
)

# .
#   .--cluster-------------------------------------------------------------.
#   |                         _           _                                |
#   |                     ___| |_   _ ___| |_ ___ _ __                     |
#   |                    / __| | | | / __| __/ _ \ '__|                    |
#   |                   | (__| | |_| \__ \ ||  __/ |                       |
#   |                    \___|_|\__,_|___/\__\___|_|                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_storeonce_clusterinfo_cluster(section: Section) -> DiscoveryResult:
    if "Cluster Health" in section:
        yield Service()


# this seems to be a HaSI plugin
def check_storeonce_clusterinfo_cluster(section: Section) -> CheckResult:
    yield Result(state=State.OK, summary=f"Cluster Status: {section['Cluster Status']}")
    yield Result(state=State.OK, summary=f"Replication Status: {section['Replication Status']}")

    # Check state of components
    for component in ("Cluster Health", "Replication Health"):
        yield Result(
            state=storeonce.STATE_MAP[section["%s Level" % component]],
            notice=f"{component}: {section[component]}",
        )


check_plugin_storeonce_clusterinfo_cluster = CheckPlugin(
    name="storeonce_clusterinfo_cluster",
    service_name="Appliance Status",
    sections=["storeonce_clusterinfo"],
    discovery_function=discover_storeonce_clusterinfo_cluster,
    check_function=check_storeonce_clusterinfo_cluster,
)


# .
#   .--cluster space-------------------------------------------------------.
#   |           _           _                                              |
#   |       ___| |_   _ ___| |_ ___ _ __   ___ _ __   __ _  ___ ___        |
#   |      / __| | | | / __| __/ _ \ '__| / __| '_ \ / _` |/ __/ _ \       |
#   |     | (__| | |_| \__ \ ||  __/ |    \__ \ |_) | (_| | (_|  __/       |
#   |      \___|_|\__,_|___/\__\___|_|    |___/ .__/ \__,_|\___\___|       |
#   |                                         |_|                          |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_storeonce_clusterinfo_space(section: Section) -> DiscoveryResult:
    yield Service(item="Total Capacity")


check_plugin_storeonce_clusterinfo_space = CheckPlugin(
    name="storeonce_clusterinfo_space",
    service_name="%s",
    sections=["storeonce_clusterinfo"],
    discovery_function=discover_storeonce_clusterinfo_space,
    check_function=storeonce.check_storeonce_space,
    check_ruleset_name="filesystem",
    check_default_parameters=df.FILESYSTEM_DEFAULT_PARAMS,
)

# .
#   .--uptime--------------------------------------------------------------.
#   |                              _   _                                   |
#   |                  _   _ _ __ | |_(_)_ __ ___   ___                    |
#   |                 | | | | '_ \| __| | '_ ` _ \ / _ \                   |
#   |                 | |_| | |_) | |_| | | | | | |  __/                   |
#   |                  \__,_| .__/ \__|_|_| |_| |_|\___|                   |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_storeonce_clusterinfo_uptime(section: Section) -> DiscoveryResult:
    yield Service()


def check_storeonce_clusterinfo_uptime(params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from uptime.check(params, uptime.Section(float(section["Uptime Seconds"]), None))


check_plugin_storeonce_clusterinfo_uptime = CheckPlugin(
    name="storeonce_clusterinfo_uptime",
    service_name="Uptime",
    sections=["storeonce_clusterinfo"],
    discovery_function=discover_storeonce_clusterinfo_uptime,
    check_function=check_storeonce_clusterinfo_uptime,
    check_ruleset_name="uptime",
    check_default_parameters={},
)
