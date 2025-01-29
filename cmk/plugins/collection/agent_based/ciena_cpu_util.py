#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping, Sequence
from typing import NamedTuple

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    OIDEnd,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.ciena_ces import DETECT_CIENA_5142, DETECT_CIENA_5171
from cmk.plugins.lib.cpu_util import check_cpu_util

Section5142 = int


class Section5171(NamedTuple):
    util: int
    cores: Sequence[tuple[str, int]]


def parse_ciena_cpu_util_5142(string_table: StringTable) -> Section5142 | None:
    """

    >>> parse_ciena_cpu_util_5142([['3', '0']])
    3
    """
    if not string_table:
        return None
    return int(string_table[0][0])


def parse_ciena_cpu_util_5171(string_table: StringTable) -> Section5171 | None:
    """

    This function deviates from how the data should be interpreted based on MIB.

    >>> parse_ciena_cpu_util_5171([['2', '1.31'], ['10', '2.31'], ['0', '3.31']])
    Section5171(util=2, cores=[('0', 10), ('1', 0)])
    """
    cores = []
    util = None
    for cpu_util, oid_end in string_table:
        index, _ = oid_end.split(".")
        if index == "1":
            util = int(cpu_util)
        else:
            index_minus_2 = str(int(index) - 2)
            cores.append((index_minus_2, int(cpu_util)))
    if util is None:
        return None
    return Section5171(util=util, cores=cores)


snmp_section_ciena_cpu_util_5142 = SimpleSNMPSection(
    name="ciena_cpu_util_5142",
    parse_function=parse_ciena_cpu_util_5142,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6141.2.60.12.1.11",
        oids=[
            "9",  # wwpLeosSystemCpuUtilizationLast60Seconds
        ],
    ),
    detect=DETECT_CIENA_5142,
)

snmp_section_ciena_cpu_util_5171 = SimpleSNMPSection(
    name="ciena_cpu_util_5171",
    parse_function=parse_ciena_cpu_util_5171,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1271.2.1.5.1.2.1.4.5.1",
        oids=[
            "4",  # cienaCesChassisCPUHealthCurrMeasurement
            OIDEnd(),
        ],
    ),
    detect=DETECT_CIENA_5171,
)


def discover_ciena_cpu_util(section: Section5171 | Section5142) -> DiscoveryResult:
    yield Service()


def check_ciena_cpu_util_5142(
    params: Mapping[str, object],
    section: Section5142,
) -> CheckResult:
    yield from check_cpu_util(
        util=section,
        params=params,
        this_time=time.time(),
        value_store=get_value_store(),
    )


def check_ciena_cpu_util_5171(
    params: Mapping[str, object],
    section: Section5171,
) -> CheckResult:
    yield from check_cpu_util(
        util=section.util,
        params=params,
        cores=section.cores,
        this_time=time.time(),
        value_store=get_value_store(),
    )


check_plugin_ciena_cpu_util_5142 = CheckPlugin(
    name="ciena_cpu_util_5142",
    service_name="CPU utilization",
    discovery_function=discover_ciena_cpu_util,
    check_function=check_ciena_cpu_util_5142,
    check_ruleset_name="cpu_utilization_os",
    check_default_parameters={
        "util": (80.0, 90.0),
    },
)

check_plugin_ciena_cpu_util_5171 = CheckPlugin(
    name="ciena_cpu_util_5171",
    service_name="CPU utilization",
    discovery_function=discover_ciena_cpu_util,
    check_function=check_ciena_cpu_util_5171,
    check_ruleset_name="cpu_utilization_os",
    check_default_parameters={
        "util": (80.0, 90.0),
    },
)
