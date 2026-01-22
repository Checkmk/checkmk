#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
from dataclasses import dataclass

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.omd.agent_based.omd_diskusage import check, discovery, parse, Section

TABLE = [
    [l]
    for l in """[site heute]
110891421231        /omd/sites/heute
11089142        /omd/sites/heute/var/log
110460211219    /omd/sites/heute/var/check_mk/rrd
[site test]
4096    /omd/sites/test/var/check_mk/rrd
16668   /omd/sites/test/var/log
26668   /omd/sites/test
""".split("\n")
]

TABLE_2 = [
    [l]
    for l in """[site log]
229473382	/omd/sites/log
96979	/omd/sites/log/var/log
123481264	/omd/sites/log/var/check_mk/rrd
4096	/omd/sites/log/tmp/
323595	/omd/sites/log/local/
43255425	/omd/sites/log/var/check_mk/agents/
1648718	/omd/sites/log/var/check_mk/core/
[site local]
258890373	/omd/sites/local
827498	/omd/sites/local/var/log
152635621	/omd/sites/local/var/check_mk/rrd
12288	/omd/sites/local/tmp/
323595	/omd/sites/local/local/
43169326	/omd/sites/local/var/check_mk/agents/
4096    /omd/sites/local/var/mkeventd/history/
743561	/omd/sites/local/var/check_mk/core/
13208	/omd/sites/local/var/check_mk/inventory_archive/
666	/omd/sites/local/var/check_mk/crashes/
1099	/omd/sites/local/var/check_mk/otel_collector/
49475	/omd/sites/local/var/clickhouse-server/
""".split("\n")
]


@pytest.fixture(name="section")
def _section() -> Section:
    return parse(TABLE)


@pytest.fixture(name="section_v2")
def _section_v2() -> Section:
    return parse(TABLE_2)


def test_parsing_deals_with_missing_total() -> None:
    assert parse([["[site no-total-available]"], ["1234 /omd/sites/no-total-available/tmp/"]])[
        "no-total-available"
    ]


def test_discovery(section: Section) -> None:
    services = list(discovery(section))
    assert services == [Service(item="heute"), Service(item="test")]


def test_discovery_v2(section_v2: Section) -> None:
    services = list(discovery(section_v2))
    assert services == [Service(item="log"), Service(item="local")]


@dataclass
class SiteTest:
    item: str
    expected_results: list[Result]
    expected_metrics: list[Metric]


Sites = [
    pytest.param(
        SiteTest(
            item="heute",
            expected_results=[
                Result(state=State.OK, summary="Total: 103 GiB"),
                Result(state=State.OK, summary="Logs: 10.6 MiB"),
                Result(state=State.OK, summary="RRDs: 103 GiB"),
            ],
            expected_metrics=[
                Metric("omd_size", 110891421231),
                Metric("omd_log_size", 11089142),
                Metric("omd_rrd_size", 110460211219),
            ],
        ),
        id="heute",
    ),
    pytest.param(
        SiteTest(
            item="test",
            expected_results=[
                Result(state=State.OK, summary="Total: 26.0 KiB"),
                Result(state=State.OK, summary="Logs: 16.3 KiB"),
                Result(state=State.OK, summary="RRDs: 4.00 KiB"),
            ],
            expected_metrics=[
                Metric("omd_size", 26668),
                Metric("omd_log_size", 16668),
                Metric("omd_rrd_size", 4096),
            ],
        ),
        id="test",
    ),
]


@pytest.mark.parametrize("site", Sites)
def test_check(site: SiteTest, section: Section) -> None:
    check_results = list(check(item=site.item, section=section))
    results = [r for r in check_results if isinstance(r, Result)]
    metrics = [m for m in check_results if isinstance(m, Metric)]
    assert metrics == site.expected_metrics
    assert results == site.expected_results


SitesV2 = [
    pytest.param(
        SiteTest(
            item="log",
            expected_results=[
                Result(state=State.OK, summary="Total: 219 MiB"),
                Result(state=State.OK, summary="Agents: 41.3 MiB"),
                Result(state=State.OK, summary="Core: 1.57 MiB"),
                Result(state=State.OK, summary="Local: 316 KiB"),
                Result(state=State.OK, summary="Logs: 94.7 KiB"),
                Result(state=State.OK, summary="RRDs: 118 MiB"),
                Result(state=State.OK, summary="Tmp: 4.00 KiB"),
            ],
            expected_metrics=[
                Metric("omd_size", 229473382.0),
                Metric("omd_agents_size", 43255425.0),
                Metric("omd_core_size", 1648718.0),
                Metric("omd_local_size", 323595.0),
                Metric("omd_log_size", 96979.0),
                Metric("omd_rrd_size", 123481264.0),
                Metric("omd_tmp_size", 4096.0),
            ],
        ),
        id="log",
    ),
    pytest.param(
        SiteTest(
            item="local",
            expected_results=[
                Result(state=State.OK, summary="Total: 247 MiB"),
                Result(state=State.OK, summary="Agents: 41.2 MiB"),
                Result(state=State.OK, summary="Core: 726 KiB"),
                Result(state=State.OK, summary="Crashes: 666 B"),
                Result(state=State.OK, summary="History: 4.00 KiB"),
                Result(state=State.OK, summary="Inventory: 12.9 KiB"),
                Result(state=State.OK, summary="Local: 316 KiB"),
                Result(state=State.OK, summary="Logs: 808 KiB"),
                Result(state=State.OK, summary="Metric backend: 48.3 KiB"),
                Result(state=State.OK, summary="OTel: 1.07 KiB"),
                Result(state=State.OK, summary="RRDs: 146 MiB"),
                Result(state=State.OK, summary="Tmp: 12.0 KiB"),
            ],
            expected_metrics=[
                Metric("omd_size", 258890373.0),
                Metric("omd_agents_size", 43169326.0),
                Metric("omd_core_size", 743561.0),
                Metric("omd_crashes_size", 666.0),
                Metric("omd_history_size", 4096.0),
                Metric("omd_inventory_size", 13208.0),
                Metric("omd_local_size", 323595.0),
                Metric("omd_log_size", 827498.0),
                Metric("omd_metric_backend_size", 49475.0),
                Metric("omd_otel_collector_size", 1099.0),
                Metric("omd_rrd_size", 152635621.0),
                Metric("omd_tmp_size", 12288.0),
            ],
        ),
        id="local",
    ),
]


@pytest.mark.parametrize("site", SitesV2)
def test_check_v2(site: SiteTest, section_v2: Section) -> None:
    check_results = list(check(item=site.item, section=section_v2))
    results = [r for r in check_results if isinstance(r, Result)]
    metrics = [m for m in check_results if isinstance(m, Metric)]
    assert metrics == site.expected_metrics
    assert results == site.expected_results
