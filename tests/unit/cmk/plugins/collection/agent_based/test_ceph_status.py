#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from functools import lru_cache

from cmk.agent_based.v2 import get_value_store, Result, State
from cmk.plugins.collection.agent_based import ceph_status

STRING_TABLE_1 = [
    ["{"],
    ['"health":', "{"],
    ['"status":', '"HEALTH_OK",'],
    ['"checks":', "{},"],
    ['"mutes":', "[]"],
    ["},"],
    ['"election_epoch":', "175986,"],
    ['"mgrmap":', "{"],
    ['"available":', "true,"],
    ['"num_standbys":', "3,"],
    ['"modules":', "["],
    ['"dashboard",'],
    ['"diskprediction_local",'],
    ['"restful",'],
    ['"status"'],
    ["],"],
    ['"services":', "{"],
    ['"dashboard":', '"http://gcd-virthost4.ad.gcd.de:8080/"'],
    ["}"],
    ["},"],
    ['"progress_events":', "{}"],
    ["}"],
]

STRING_TABLE_OSDS = [
    ["{"],
    ['"health":', "{"],
    ['"status":', '"HEALTH_OK",'],
    ['"checks":', "{},"],
    ['"mutes":', "[]"],
    ["},"],
    ['"election_epoch":', "175986,"],
    ['"osdmap":', "{"],
    ['"epoch":', "54070,"],
    ['"num_osds":', "32,"],
    ['"num_up_osds":', "32,"],
    ['"osd_up_since":', "1605039365,"],
    ['"num_in_osds":', "32,"],
    ['"osd_in_since":', "1605039365,"],
    ['"num_remapped_pgs":', "0"],
    ["},"],
    ['"progress_events":', "{}"],
    ["}"],
]


@lru_cache
def section1() -> ceph_status.Section:
    return ceph_status.parse_ceph_status(STRING_TABLE_1)


@lru_cache
def section_osds() -> ceph_status.Section:
    return ceph_status.parse_ceph_status(STRING_TABLE_OSDS)


def test_check_ceph_status(initialised_item_state: None) -> None:
    get_value_store().update({"ceph_status.epoch.rate": (0, 175986)})
    assert list(ceph_status.check_ceph_status({"epoch": (1, 3, 30)}, section1())) == [
        Result(state=State.OK, summary="Health: OK"),
        Result(state=State.OK, summary="Epoch rate (30 minutes 0 seconds average): 0.00"),
    ]
    assert not list(ceph_status.check_ceph_status_mgrs({"epoch": (1, 2, 5)}, section1()))


def test_check_ceph_status_osds(initialised_item_state: None) -> None:
    get_value_store().update({"ceph_status.epoch.rate": (0, 175986)})
    assert list(
        ceph_status.check_ceph_status(
            {
                "epoch": (50, 100, 15),
                "num_out_osds": (7.0, 5.0),
                "num_down_osds": (7.0, 5.0),
            },
            section_osds(),
        )
    ) == [
        Result(state=State.OK, summary="Health: OK"),
        Result(state=State.OK, summary="Epoch rate (15 minutes 0 seconds average): 0.00"),
    ]
