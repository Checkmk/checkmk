#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
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

import pytest

from cmk.agent_based import v3_unstable


def _names(space: ModuleType) -> set[str]:
    return {n for n in dir(space) if not n.startswith("_")}


def test_v3_unstable() -> None:
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
    assert _names(v3_unstable) == expected


def test_v3_unstable_render() -> None:
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
    assert _names(v3_unstable.render) == expected


def test_v3_unstable_clusterize() -> None:
    expected = {"make_node_notice_results"}
    assert _names(v3_unstable.clusterize) == expected


def test_v3_unstable_metric_has_lower_levels() -> None:
    m = v3_unstable.Metric("temperature", 42.0, levels=(80.0, 90.0), lower_levels=(5.0, 0.0))
    assert m.lower_levels == (5.0, 0.0)


@pytest.mark.parametrize(
    "lower_levels",
    [
        (5.0, 0.0),
        (None, None),
        (5.0, None),
        (None, 0.0),
    ],
)
def test_v3_unstable_metric_lower_levels_variants(
    lower_levels: tuple[float | None, float | None],
) -> None:
    m = v3_unstable.Metric("cpu", 50.0, lower_levels=lower_levels)
    assert m.lower_levels == lower_levels
