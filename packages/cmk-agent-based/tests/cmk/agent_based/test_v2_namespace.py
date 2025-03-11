#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
+---------------------------------------------------------+
|              Achtung Alles Lookenskeepers!              |
|              =============================              |
|                                                         |
| The extend of the Check API is well documented, and the |
| result of careful negotiation. It should not be changed |
| light heartedly!                                        |
+---------------------------------------------------------+
"""

from types import ModuleType

from cmk.agent_based import v2


def _names(space: ModuleType) -> set[str]:
    return {n for n in dir(space) if not n.startswith("_")}


def test_v2() -> None:
    expected = {
        "entry_point_prefixes",
        "AgentParseFunction",
        "AgentSection",
        "SimpleSNMPSection",
        "SNMPSection",
        "CheckPlugin",
        "InventoryPlugin",
        "CheckResult",
        "DiscoveryResult",
        "HostLabelGenerator",
        "InventoryResult",
        "StringByteTable",
        "StringTable",
        "RuleSetType",
        "Attributes",
        "GetRateError",
        "HostLabel",
        "IgnoreResults",
        "IgnoreResultsError",
        "Metric",
        "OIDBytes",
        "OIDCached",
        "OIDEnd",
        "Result",
        "SNMPTree",
        "SNMPDetectSpecification",
        "Service",
        "ServiceLabel",
        "State",
        "TableRow",
        "all_of",
        "any_of",
        "check_levels",
        "NoLevelsT",
        "FixedLevelsT",
        "PredictiveLevelsT",
        "LevelsT",
        "clusterize",
        "contains",
        "endswith",
        "equals",
        "exists",
        "get_average",
        "get_rate",
        "get_value_store",
        "matches",
        "not_contains",
        "not_endswith",
        "not_equals",
        "not_exists",
        "not_matches",
        "not_startswith",
        "render",
        "startswith",
    }
    assert _names(v2) == expected


def test_v2_render() -> None:
    expected = {
        "bytes",
        "date",
        "datetime",
        "disksize",
        "filesize",
        "frequency",
        "iobandwidth",
        "networkbandwidth",
        "nicspeed",
        "percent",
        "timespan",
        "time_offset",
    }
    assert _names(v2.render) == expected


def test_v1_clusterize() -> None:
    expected = {"make_node_notice_results"}
    assert _names(v2.clusterize) == expected
