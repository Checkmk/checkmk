#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Iterator, Mapping
from typing import Any

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import all_of, exists, SNMPTree, startswith, StringTable
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util

check_info = {}


def check_netapp_cpu(
    item: None, params: Mapping[str, Any], info: StringTable
) -> Iterator[tuple[int, str, list[Any]]]:
    util = float(info[0][0])
    yield from check_cpu_util(util, params)


def parse_netapp_cpu(string_table: StringTable) -> StringTable | None:
    return string_table or None


def discover_netapp_cpu(info: StringTable) -> list[tuple[None, dict[str, object]]]:
    return [(None, {})]


check_info["netapp_cpu"] = LegacyCheckDefinition(
    name="netapp_cpu",
    parse_function=parse_netapp_cpu,
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.1.0", "NetApp Release"), exists(".1.3.6.1.4.1.789.1.2.1.3.0")
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.789.1.2.1",
        oids=["3"],
    ),
    service_name="CPU utilization",
    discovery_function=discover_netapp_cpu,
    check_function=check_netapp_cpu,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (80.0, 90.0)},
)
