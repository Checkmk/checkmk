#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.collection.agent_based import emc_isilon_quota as eiq
from cmk.plugins.lib import df

STRING_TABLE = [["/ifs/data/pacs", "0", "1", "219902325555200", "0", "0", "3844608548041"]]


@pytest.fixture(name="section", scope="module")
def _get_section() -> eiq.Section:
    return eiq.parse_emc_isilon_quota(STRING_TABLE)


def test_discovery(section: eiq.Section) -> None:
    assert list(eiq.discover_emc_isilon_quota([{"groups": []}], section)) == [
        Service(item="/ifs/data/pacs"),
    ]


def test_check(section: eiq.Section, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        eiq,
        "get_value_store",
        lambda: {
            "/ifs/data/pacs.delta": (1657628373.6628969, 3666504.428902626),
        },
    )

    assert list(
        eiq.check_emc_isilon_quota("/ifs/data/pacs", df.FILESYSTEM_DEFAULT_PARAMS, section)
    ) == [
        Metric(
            "fs_used",
            3666504.428902626,
            levels=(167772160.0, 188743680.0),
            boundaries=(0.0, 209715200.0),
        ),
        Metric("fs_free", 206048695.57109737, boundaries=(0, None)),
        Metric("fs_used_percent", 1.7483255524171002, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
        Result(state=State.OK, summary="Used: 1.75% - 3.50 TiB of 200 TiB"),
        Metric("fs_size", 209715200.0, boundaries=(0, None)),
        Metric("growth", 0.0),
        Result(state=State.OK, summary="trend per 1 day 0 hours: +0 B"),
        Result(state=State.OK, summary="trend per 1 day 0 hours: +0%"),
        Metric("trend", 0.0),
    ]
