#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

import pytest

from cmk.base.plugins.agent_based import aix_diskiod
from cmk.base.plugins.agent_based.agent_based_api.v1 import IgnoreResultsError, Metric, Result
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state

DISK = {
    "read_throughput": 2437253982208,
    "write_throughput": 12421567621120,
}


def test_parse_aix_diskiod():
    assert aix_diskiod.parse_aix_diskiod(
        [
            ["hdisk0", "5.1", "675.7", "46.5", "2380130842", "12130437130"],
            ["hdisk0000", "58.5", "19545.1", "557.3", "%l", "%l"],
        ],
    ) == {
        "hdisk0": DISK,
    }


def test_check_disk():
    value_store: dict[str, Any] = {}
    now = 1647029464.27418

    with pytest.raises(IgnoreResultsError):
        list(aix_diskiod._check_disk({}, DISK, value_store, now))

    assert list(aix_diskiod._check_disk({}, DISK, value_store, now + 60)) == [
        Result(state=state.OK, summary="Read: 0.00 B/s"),
        Metric("disk_read_throughput", 0.0),
        Result(state=state.OK, summary="Write: 0.00 B/s"),
        Metric("disk_write_throughput", 0.0),
    ]


def _test_check_aix_diskiod(item, section_1, section_2, check_func):

    value_store: dict[str, Any] = {}

    # fist call: initialize value store
    with pytest.raises(IgnoreResultsError):
        list(
            check_func(
                item,
                {},
                section_1,
                value_store,
                0.0,
            )
        )

    # second call: get values
    check_results = list(
        check_func(
            item,
            {},
            section_2,
            value_store,
            60,
        )
    )
    for res in check_results:
        if isinstance(res, Metric):
            assert res.value > 0


DISK_HALF = {k: int(v / 2) for k, v in DISK.items()}


@pytest.mark.parametrize(
    "item",
    ["item", "SUMMARY"],
)
def test_check_aix_diskiod(item):
    _test_check_aix_diskiod(
        item,
        {
            item: DISK_HALF,
        },
        {
            item: DISK,
        },
        aix_diskiod._check_aix_diskiod,
    )


@pytest.mark.parametrize(
    "item",
    ["item", "SUMMARY"],
)
def test_cluster_check_aix_diskiod(item):
    _test_check_aix_diskiod(
        item,
        {
            "node1": {
                item: DISK_HALF,
            },
            "node2": {
                item: DISK_HALF,
            },
        },
        {
            "node1": {
                item: DISK,
            },
            "node2": {
                item: DISK,
            },
        },
        aix_diskiod._cluster_check_aix_diskiod,
    )
