#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

import pytest  # type: ignore[import]

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    get_rate,
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    State as state,
    type_defs,
)
from cmk.base.plugins.agent_based.utils import diskstat


@pytest.mark.parametrize(
    "params,exp_res",
    [
        (
            [
                type_defs.Parameters({
                    'summary': True,
                },),
            ],
            [
                Service(item='SUMMARY'),
            ],
        ),
        (
            [
                type_defs.Parameters({
                    'summary': True,
                    'physical': True,
                },),
            ],
            [
                Service(item='SUMMARY'),
                Service(item='disk1'),
                Service(item='disk2'),
            ],
        ),
        (
            [
                type_defs.Parameters(
                    {
                        'summary': True,
                        'physical': True,
                        'lvm': True,
                        'vxvm': True,
                        'diskless': True,
                    },),
            ],
            [
                Service(item='SUMMARY'),
                Service(item='disk1'),
                Service(item='disk2'),
                Service(item='LVM disk'),
                Service(item='VxVM disk'),
                Service(item='xsd0 disk'),
            ],
        ),
    ],
)
def test_discovery_diskstat_generic(params, exp_res):
    assert list(
        diskstat.discovery_diskstat_generic(
            params,
            {
                'disk1': {},
                'disk2': {},
                'LVM disk': {},
                'VxVM disk': {},
                'xsd0 disk': {},
            },
        )) == exp_res


DISK = {
    'utilization': 0.53242,
    'read_throughput': 12312.4324,
    'write_throughput': 3453.345,
    'average_wait': 30,
    'average_read_wait': 123,
    'average_write_wait': 90,
    'latency': 2,
    'read_latency': 3,
    'write_latency': 4,
    'queue_length': 123,
    'read_ql': 90,
    'write_ql': 781,
    'read_ios': 12379.435345,
    'write_ios': 8707809.98289,
    'x': 0,
    'y': 1,
}


def _compute_rates_single_disk(
    disk,
    value_store,
    value_store_suffix='.',
):
    disk_w_rates = {}
    raise_ignore_res_error = False
    now = time.time()

    for key, value in disk.items():
        try:
            disk_w_rates[key] = get_rate(
                value_store,
                key + value_store_suffix,
                now,
                value,
            )
        except IgnoreResultsError:
            raise_ignore_res_error = True

    if raise_ignore_res_error:
        raise IgnoreResultsError

    return disk_w_rates


def test_compute_rates_multiple_disks():
    disks = {
        'C:': DISK,
        'D:': DISK,
    }
    value_store: type_defs.ValueStore = {}

    # first call should result in IgnoreResultsError, second call should yield rates
    with pytest.raises(IgnoreResultsError):
        diskstat.compute_rates_multiple_disks(
            disks,
            value_store,
            _compute_rates_single_disk,
        )
    disks_w_rates = diskstat.compute_rates_multiple_disks(
        disks,
        value_store,
        _compute_rates_single_disk,
    )

    for (name_in, disk_in), (name_out, disk_out) in zip(
            iter(disks.items()),
            iter(disks_w_rates.items()),
    ):
        assert name_in == name_out
        assert disk_out == {k: 0 for k in disk_in}


DISKS = [
    [
        {
            'a': 3,
            'b': 3,
        },
        {
            'a': 5.5345,
            'c': 0.,
        },
    ],
    [
        {
            'a': 3,
            'utilization': 3,
        },
        {
            'a': 5.5345,
            'c': 0.,
            'average_x': 0,
        },
        {
            'a': 5.5345,
            'utilization': 0.897878,
        },
        {
            'average_x': 123.123123,
            'average_y': 89,
        },
    ],
]


@pytest.mark.parametrize(
    "disks",
    DISKS,
)
def test_combine_disks(disks):
    combined_disk = diskstat.combine_disks(disks)
    # any key found in at least one of the input dicts must be present in the combination
    assert sorted(combined_disk) == sorted(set(sum((list(disk) for disk in disks), [])))

    for key, val in combined_disk.items():
        exp_res = sum(disk.get(key, 0.) for disk in disks)
        if key.startswith("ave") or key in ("utilization", "latency", "queue_length"):
            assert val == exp_res / sum(key in disk for disk in disks)
        else:
            assert val == exp_res


@pytest.mark.parametrize(
    "disks",
    DISKS,
)
def test_summarize_disks(disks):
    assert diskstat.summarize_disks(('a', disk) for disk in disks) == diskstat.combine_disks(disks)
    assert diskstat.summarize_disks(
        ('LVM ' if i == 0 else 'b', disk)
        for i, disk in enumerate(disks)) == diskstat.combine_disks(disks[1:])


@pytest.mark.parametrize(
    "levels,factor",
    [
        (
            (
                1,
                2,
            ),
            3,
        ),
        (
            (
                10,
                20,
            ),
            1e6,
        ),
        (
            None,
            1,
        ),
    ],
)
def test_scale_levels(levels, factor):
    scaled_levels = diskstat._scale_levels(levels, factor)
    if levels is None:
        assert scaled_levels is None
    else:
        assert scaled_levels == tuple(level * factor for level in levels)


@pytest.mark.parametrize(
    "params,disk,exp_res",
    [
        (
            type_defs.Parameters({}),
            DISK,
            [
                Result(state=state.OK, summary='Utilization: 53.2%', details='Utilization: 53.2%'),
                Metric('disk_utilization', 0.53242, levels=(None, None), boundaries=(None, None)),
                Result(state=state.OK,
                       summary='Read throughput: 12.3 kB/s',
                       details='Read throughput: 12.3 kB/s'),
                Metric('disk_read_throughput',
                       12312.4324,
                       levels=(None, None),
                       boundaries=(None, None)),
                Result(state=state.OK,
                       summary='Write throughput: 3.45 kB/s',
                       details='Write throughput: 3.45 kB/s'),
                Metric(
                    'disk_write_throughput', 3453.345, levels=(None, None),
                    boundaries=(None, None)),
                Result(state=state.OK,
                       summary='Average wait: 30 seconds',
                       details='Average wait: 30 seconds'),
                Metric('disk_average_wait', 30.0, levels=(None, None), boundaries=(None, None)),
                Result(state=state.OK,
                       summary='Average read wait: 2 minutes 3 seconds',
                       details='Average read wait: 2 minutes 3 seconds'),
                Metric(
                    'disk_average_read_wait', 123.0, levels=(None, None), boundaries=(None, None)),
                Result(state=state.OK,
                       summary='Average write wait: 1 minute 30 seconds',
                       details='Average write wait: 1 minute 30 seconds'),
                Metric(
                    'disk_average_write_wait', 90.0, levels=(None, None), boundaries=(None, None)),
                Result(state=state.OK, summary='Latency: 2 seconds', details='Latency: 2 seconds'),
                Metric('disk_latency', 2.0, levels=(None, None), boundaries=(None, None)),
                Result(state=state.OK,
                       summary='Read latency: 3 seconds',
                       details='Read latency: 3 seconds'),
                Metric('disk_read_latency', 3.0, levels=(None, None), boundaries=(None, None)),
                Result(state=state.OK,
                       summary='Write latency: 4 seconds',
                       details='Write latency: 4 seconds'),
                Metric('disk_write_latency', 4.0, levels=(None, None), boundaries=(None, None)),
                Result(state=state.OK,
                       summary='Average queue length: 123.00',
                       details='Average queue length: 123.00'),
                Metric('disk_queue_length', 123.0, levels=(None, None), boundaries=(None, None)),
                Result(state=state.OK,
                       summary='Average read queue length: 90.00',
                       details='Average read queue length: 90.00'),
                Metric('disk_read_ql', 90.0, levels=(None, None), boundaries=(None, None)),
                Result(state=state.OK,
                       summary='Average write queue length: 781.00',
                       details='Average write queue length: 781.00'),
                Metric('disk_write_ql', 781.0, levels=(None, None), boundaries=(None, None)),
                Result(state=state.OK,
                       summary='Read operations: 12379.44/s',
                       details='Read operations: 12379.44/s'),
                Metric('disk_read_ios', 12379.435345, levels=(None, None), boundaries=(None, None)),
                Result(state=state.OK,
                       summary='Write operations: 8707809.98/s',
                       details='Write operations: 8707809.98/s'),
                Metric(
                    'disk_write_ios', 8707809.98289, levels=(None, None), boundaries=(None, None)),
                Metric('disk_x', 0.0, levels=(None, None), boundaries=(None, None)),
                Metric('disk_y', 1.0, levels=(None, None), boundaries=(None, None)),
            ],
        ),
        (
            type_defs.Parameters({
                'utilization': (10, 20),
                'read': (1e-5, 1e-4),
                'write': (1e-5, 1e-4),
                'latency': (1e3, 2e3),
                'read_latency': (1e3, 2e3),
                'write_latency': (1e3, 2e3),
                'read_wait': (1e3, 2e3),
                'write_wait': (1e3, 2e3),
                'read_ios': (1e4, 1e5),
                'write_ios': (1e5, 1e6),
            }),
            DISK,
            [
                Result(state=state.CRIT,
                       summary='Utilization: 53.2% (warn/crit at 10.0%/20.0%)',
                       details='Utilization: 53.2% (warn/crit at 10.0%/20.0%)'),
                Metric('disk_utilization', 0.53242, levels=(0.1, 0.2), boundaries=(None, None)),
                Result(state=state.CRIT,
                       summary='Read throughput: 12.3 kB/s (warn/crit at 10.0 B/s/100 B/s)',
                       details='Read throughput: 12.3 kB/s (warn/crit at 10.0 B/s/100 B/s)'),
                Metric('disk_read_throughput',
                       12312.4324,
                       levels=(10.0, 100.0),
                       boundaries=(None, None)),
                Result(state=state.CRIT,
                       summary='Write throughput: 3.45 kB/s (warn/crit at 10.0 B/s/100 B/s)',
                       details='Write throughput: 3.45 kB/s (warn/crit at 10.0 B/s/100 B/s)'),
                Metric('disk_write_throughput',
                       3453.345,
                       levels=(10.0, 100.0),
                       boundaries=(None, None)),
                Result(state=state.OK,
                       summary='Average wait: 30 seconds',
                       details='Average wait: 30 seconds'),
                Metric('disk_average_wait', 30.0, levels=(None, None), boundaries=(None, None)),
                Result(state=state.CRIT,
                       summary=
                       'Average read wait: 2 minutes 3 seconds (warn/crit at 1 second/2 seconds)',
                       details=
                       'Average read wait: 2 minutes 3 seconds (warn/crit at 1 second/2 seconds)'),
                Metric('disk_average_read_wait', 123.0, levels=(1.0, 2.0), boundaries=(None, None)),
                Result(state=state.CRIT,
                       summary=
                       'Average write wait: 1 minute 30 seconds (warn/crit at 1 second/2 seconds)',
                       details=
                       'Average write wait: 1 minute 30 seconds (warn/crit at 1 second/2 seconds)'),
                Metric('disk_average_write_wait', 90.0, levels=(1.0, 2.0), boundaries=(None, None)),
                Result(state=state.CRIT,
                       summary='Latency: 2 seconds (warn/crit at 1 second/2 seconds)',
                       details='Latency: 2 seconds (warn/crit at 1 second/2 seconds)'),
                Metric('disk_latency', 2.0, levels=(1.0, 2.0), boundaries=(None, None)),
                Result(state=state.CRIT,
                       summary='Read latency: 3 seconds (warn/crit at 1 second/2 seconds)',
                       details='Read latency: 3 seconds (warn/crit at 1 second/2 seconds)'),
                Metric('disk_read_latency', 3.0, levels=(1.0, 2.0), boundaries=(None, None)),
                Result(state=state.CRIT,
                       summary='Write latency: 4 seconds (warn/crit at 1 second/2 seconds)',
                       details='Write latency: 4 seconds (warn/crit at 1 second/2 seconds)'),
                Metric('disk_write_latency', 4.0, levels=(1.0, 2.0), boundaries=(None, None)),
                Result(state=state.OK,
                       summary='Average queue length: 123.00',
                       details='Average queue length: 123.00'),
                Metric('disk_queue_length', 123.0, levels=(None, None), boundaries=(None, None)),
                Result(state=state.OK,
                       summary='Average read queue length: 90.00',
                       details='Average read queue length: 90.00'),
                Metric('disk_read_ql', 90.0, levels=(None, None), boundaries=(None, None)),
                Result(state=state.OK,
                       summary='Average write queue length: 781.00',
                       details='Average write queue length: 781.00'),
                Metric('disk_write_ql', 781.0, levels=(None, None), boundaries=(None, None)),
                Result(state=state.WARN,
                       summary='Read operations: 12379.44/s (warn/crit at 10000.00/s/100000.00/s)',
                       details='Read operations: 12379.44/s (warn/crit at 10000.00/s/100000.00/s)'),
                Metric('disk_read_ios',
                       12379.435345,
                       levels=(10000.0, 100000.0),
                       boundaries=(None, None)),
                Result(
                    state=state.CRIT,
                    summary='Write operations: 8707809.98/s (warn/crit at 100000.00/s/1000000.00/s)',
                    details='Write operations: 8707809.98/s (warn/crit at 100000.00/s/1000000.00/s)'
                ),
                Metric('disk_write_ios',
                       8707809.98289,
                       levels=(100000.0, 1000000.0),
                       boundaries=(None, None)),
                Metric('disk_x', 0.0, levels=(None, None), boundaries=(None, None)),
                Metric('disk_y', 1.0, levels=(None, None), boundaries=(None, None)),
            ],
        ),
        (
            type_defs.Parameters({}),
            {},
            [],
        ),
    ],
)
def test_check_diskstat_dict(params, disk, exp_res):
    value_store: type_defs.ValueStore = {}

    assert list(diskstat.check_diskstat_dict(params, disk, value_store)) == exp_res

    if exp_res:
        exp_res[0] = Result(
            state=exp_res[0].state,
            summary="5 minutes 0 seconds average: " + exp_res[0].summary,
        )

    assert list(
        diskstat.check_diskstat_dict(type_defs.Parameters({
            **params, 'average': 300
        },), disk, value_store),) == exp_res
