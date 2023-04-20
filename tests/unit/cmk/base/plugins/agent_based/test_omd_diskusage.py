#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
from dataclasses import dataclass

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.omd_diskusage import check, discovery, parse, Section

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
""".split(
        "\n"
    )
]


@pytest.fixture(name="section")
def _section() -> Section:
    return parse(TABLE)


def test_discovery(section: Section) -> None:
    services = list(discovery(section))
    assert services == [Service(item="heute"), Service(item="test")]


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
