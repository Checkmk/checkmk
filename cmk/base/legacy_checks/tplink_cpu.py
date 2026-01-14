#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.plugins.tplink.lib import DETECT_TPLINK

check_info = {}


def discover_tplink_cpu(info):
    if len(info) >= 1:
        yield None, {}


def check_tplink_cpu(_no_item, params, info):
    num_cpus = 0
    util = 0.0
    cores = []
    for line in info:
        core_util = int(line[0])
        cores.append(("core%d" % num_cpus, core_util))
        util += core_util
        num_cpus += 1

    if not num_cpus:
        return None

    util = float(util) / num_cpus
    return check_cpu_util(util, params, cores=cores)


# Migration NOTE: Create a separate section, but a common check plug-in for
# tplink_cpu, hr_cpu, cisco_nexus_cpu, bintec_cpu, winperf_processor,
# lxc_container_cpu, docker_container_cpu.
# Migration via cmk/update_config.py!
def parse_tplink_cpu(string_table: StringTable) -> StringTable:
    return string_table


check_info["tplink_cpu"] = LegacyCheckDefinition(
    name="tplink_cpu",
    parse_function=parse_tplink_cpu,
    detect=DETECT_TPLINK,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11863.6.4.1.1.1.1",
        oids=["2"],
    ),
    service_name="CPU utilization",
    discovery_function=discover_tplink_cpu,
    check_function=check_tplink_cpu,
    check_ruleset_name="cpu_utilization_os",
)
