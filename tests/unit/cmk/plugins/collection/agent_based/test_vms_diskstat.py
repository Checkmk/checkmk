#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import Service
from cmk.plugins.collection.agent_based import vms_diskstat
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS

STRING_TABLE = [
    ["$1$DGA1122:", "TEST_WORK", "1171743836", "1102431184", "0.00"],
    ["DSA3:", "SHAD_3", "66048000", "46137546", "1.57"],
    ["$1$DGA1123:", "TEST_WORK", "2171743836", "1102431184", "0.00"],
    ["$1$DGA1124:", "TEMP_02", "3171743836", "102431184", "1.10"],
    ["$1$DGA1125:", "DATA_01", "1171743836", "202431184", "0.20"],
]


@pytest.fixture(name="section", scope="module")
def _get_section() -> vms_diskstat.Section:
    return vms_diskstat.parse_vms_diskstat(STRING_TABLE)


def test_discovery(section: vms_diskstat.Section) -> None:
    assert sorted(vms_diskstat.discover_vms_diskstat_df([{"groups": []}], section)) == sorted(
        [
            Service(item="TEMP_02"),
            Service(item="DATA_01"),
            Service(item="TEST_WORK"),
            Service(item="SHAD_3"),
        ]
    )


def test_check(section: vms_diskstat.Section, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        vms_diskstat, "get_value_store", lambda: {"TEST_WORK.delta": (0, 33844.068359375)}
    )
    assert list(vms_diskstat.check_vms_diskstat_df("TEST_WORK", FILESYSTEM_DEFAULT_PARAMS, section))
