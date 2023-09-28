#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.netapp_api_luns import (
    _check_netapp_api_luns,
    discover_netapp_api_luns,
    parse_netapp_api_luns,
)
from cmk.base.plugins.agent_based.utils.netapp_api import SectionSingleInstance

STRING_TABLE = [
    [
        "lun /vol/iscsi_crm_dblogs/crm_dblogs_lu01",
        "read-only false",
        "size 644286182400",
        "vserver ISCSI_CRM",
        "size-used 538924421120",
        "online true",
        "volume iscsi_crm_dblogs",
    ],
    [
        "lun /vol/iscsi_crm_dbprod/crm_dbprod_lu01",
        "read-only false",
        "size 2638883681280",
        "vserver ISCSI_CRM",
        "size-used 2362467872768",
        "online true",
        "volume iscsi_crm_dbprod",
    ],
    [
        "lun /vol/iscsi_crm_dbtemp/crm_dbtemp_lu01",
        "read-only false",
        "size 697997260800",
        "vserver ISCSI_CRM",
        "size-used 582014812160",
        "online true",
        "volume iscsi_crm_dbtemp",
    ],
    [
        "lun /vol/iscsi_nice_db/nice_db_lun",
        "read-only false",
        "size 644286182400",
        "vserver ISCSI_NICE_NOVO",
        "size-used 435543142400",
        "online true",
        "volume iscsi_nice_db",
    ],
]


@pytest.fixture(name="section", scope="module")
def _get_section() -> SectionSingleInstance:
    return parse_netapp_api_luns(STRING_TABLE)


def test_discovery(section: SectionSingleInstance) -> None:
    assert sorted(discover_netapp_api_luns(section)) == [
        Service(item="crm_dblogs_lu01"),
        Service(item="crm_dbprod_lu01"),
        Service(item="crm_dbtemp_lu01"),
        Service(item="nice_db_lun"),
    ]


def test_checks(section: SectionSingleInstance) -> None:
    assert list(
        _check_netapp_api_luns(
            "crm_dblogs_lu01",
            {"levels": (80.0, 90.0), "trend_range": 24, "trend_perfdata": True, "read_only": False},
            section,
            {"crm_dblogs_lu01.delta": (0, 0)},
            60.0,
        )
    ) == [
        Metric(
            "fs_used",
            513958.37890625,
            levels=(491551.34765625, 552995.2661132812),
            boundaries=(0, 614439.1845703125),
        ),
        Metric("fs_free", 100480.8056640625, boundaries=(0, None)),
        Metric("fs_used_percent", 83.64674516415643, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
        Result(
            state=State.WARN,
            summary="Used: 83.65% - 502 GiB of 600 GiB (warn/crit at 80.00%/90.00% used)",
        ),
        Metric("fs_size", 614439.1845703125, boundaries=(0, None)),
        Metric("growth", 740100065.625),
        Result(state=State.OK, summary="trend per 1 day 0 hours: +706 TiB"),
        Result(state=State.OK, summary="trend per 1 day 0 hours: +120451.31%"),
        Metric("trend", 740100065.625, boundaries=(0.0, 25601.632690429688)),
        Result(state=State.OK, summary="Time left until disk full: 12 seconds"),
    ]
