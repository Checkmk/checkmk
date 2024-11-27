#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_legacy_includes.cpu_util import check_cpu_util

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.plugins.lib.sophos import DETECT_SOPHOS

check_info = {}


def parse_sophos_cpu(string_table):
    try:
        return int(string_table[0][0])
    except (ValueError, IndexError):
        return None


def check_sophos_cpu(item, params, parsed):
    return check_cpu_util(parsed, params.get("cpu_levels", (None, None)))


def discover_sophos_cpu(parsed):
    yield None, {}


check_info["sophos_cpu"] = LegacyCheckDefinition(
    name="sophos_cpu",
    detect=DETECT_SOPHOS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.21067.2.1.2.2",
        oids=["1"],
    ),
    parse_function=parse_sophos_cpu,
    service_name="CPU usage",
    discovery_function=discover_sophos_cpu,
    check_function=check_sophos_cpu,
    check_ruleset_name="sophos_cpu",
)
