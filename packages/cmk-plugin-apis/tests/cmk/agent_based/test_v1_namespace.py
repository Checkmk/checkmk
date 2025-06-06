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

from cmk.agent_based import v1


def _names(space: ModuleType) -> set[str]:
    return {n for n in dir(space) if not n.startswith("_")}


def test_v1() -> None:
    expected = {
        # value_store: not explicitly exposed here,
        "value_store",
        # register: only partially in this package, b/c that is not how we're doing things anymore.
        "register",
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
        "Service",
        "ServiceLabel",
        "State",
        "TableRow",
        "all_of",
        "any_of",
        "check_levels",
        "check_levels_predictive",
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
        "regex",
        "render",
        "startswith",
        "type_defs",
    }
    assert _names(v1) == expected


def test_v1_render() -> None:
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
    }
    assert _names(v1.render) == expected


def test_v1_type_defs() -> None:
    expected = {
        "CheckResult",
        "DiscoveryResult",
        "HostLabelGenerator",
        "InventoryResult",
        "StringByteTable",
        "StringTable",
    }
    assert _names(v1.type_defs) == expected


def test_v1_clusterize() -> None:
    expected = {"make_node_notice_results"}
    assert _names(v1.clusterize) == expected
