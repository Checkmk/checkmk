#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.base.api.agent_based import value_store
from cmk.base.plugins.agent_based.agent_based_api.v0 import (
    get_value_store,
    IgnoreResults,
    Metric,
    Result,
    state,
    type_defs,
)
from cmk.base.plugins.agent_based import aix_diskiod
from cmk.utils.type_defs import CheckPluginName

DISK = {
    'read_throughput': 2437253982208,
    'write_throughput': 12421567621120,
}


def test_parse_aix_diskiod():
    assert aix_diskiod.parse_aix_diskiod([
        ['hdisk0', '5.1', '675.7', '46.5', '2380130842', '12130437130'],
        ['hdisk0000', '58.5', '19545.1', '557.3', '%l', '%l'],
    ],) == {
        'hdisk0': DISK,
    }


def test__compute_rates():
    with value_store.context(CheckPluginName('_compute_rates'), 'item'):
        # first call should result in IngoreResults, second call should yield rates
        assert aix_diskiod._compute_rates(DISK, get_value_store())[1]
        disk_with_rates, raised_ignore = aix_diskiod._compute_rates(DISK, get_value_store())

    assert disk_with_rates == {k: 0 for k in DISK}
    assert not raised_ignore


def test__check_disk():
    with value_store.context(CheckPluginName('_check_disk'), 'item'):
        check_disk_1 = list(aix_diskiod._check_disk(type_defs.Parameters({}), DISK))
        assert len(check_disk_1)
        assert isinstance(check_disk_1[0], IgnoreResults)
        assert list(aix_diskiod._check_disk(type_defs.Parameters({}), DISK)) == [
            Result(state=state.OK, summary='Read: 0.00 B/s', details='Read: 0.00 B/s'),
            Metric('disk_read_throughput', 0.0, levels=(None, None), boundaries=(None, None)),
            Result(state=state.OK, summary='Write: 0.00 B/s', details='Write: 0.00 B/s'),
            Metric('disk_write_throughput', 0.0, levels=(None, None), boundaries=(None, None)),
        ]


def _test_check_aix_diskiod(item, section_1, section_2, check_func):
    # fist call: initialize value store
    list(check_func(
        item,
        type_defs.Parameters({}),
        section_1,
    ))

    # second call: get values
    check_results = list(check_func(
        item,
        type_defs.Parameters({}),
        section_2,
    ))
    for res in check_results:
        if isinstance(res, Metric):
            assert res.value > 0


@pytest.mark.parametrize(
    "item",
    ["item", "SUMMARY"],
)
def test_check_aix_diskiod(item):
    disk_half = {k: int(v / 2) for k, v in DISK.items()}
    with value_store.context(CheckPluginName('check_aix_diskiod'), item):
        _test_check_aix_diskiod(
            item,
            {
                'item': disk_half,
            },
            {
                'item': DISK,
            },
            aix_diskiod.check_aix_diskiod,
        )
        _test_check_aix_diskiod(
            item,
            {
                'node1': {
                    'item': disk_half,
                },
                'node2': {
                    'item': disk_half,
                },
            },
            {
                'node1': {
                    'item': DISK,
                },
                'node2': {
                    'item': DISK,
                },
            },
            aix_diskiod.cluster_check_aix_diskoid,
        )
