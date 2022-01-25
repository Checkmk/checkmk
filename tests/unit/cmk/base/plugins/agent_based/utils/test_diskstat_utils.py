#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Any, Dict, Iterable, Tuple

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    get_rate,
    IgnoreResultsError,
    Metric,
    Result,
    Service,
)
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state
from cmk.base.plugins.agent_based.utils import diskstat


@pytest.mark.parametrize(
    "params,exp_res",
    [
        (
            [
                {
                    "summary": True,
                },
            ],
            [
                Service(item="SUMMARY"),
            ],
        ),
        (
            [
                {
                    "summary": True,
                    "physical": True,
                },
            ],
            [
                Service(item="SUMMARY"),
                Service(item="disk1"),
                Service(item="disk2"),
            ],
        ),
        (
            [
                {
                    "summary": True,
                    "physical": True,
                    "lvm": True,
                    "vxvm": True,
                    "diskless": True,
                },
            ],
            [
                Service(item="SUMMARY"),
                Service(item="disk1"),
                Service(item="disk2"),
                Service(item="LVM disk"),
                Service(item="VxVM disk"),
                Service(item="xsd0 disk"),
            ],
        ),
    ],
)
def test_discovery_diskstat_generic(params, exp_res):
    assert (
        list(
            diskstat.discovery_diskstat_generic(
                params,
                {
                    "disk1": {},
                    "disk2": {},
                    "LVM disk": {},
                    "VxVM disk": {},
                    "xsd0 disk": {},
                },
            )
        )
        == exp_res
    )


DISK = {
    "utilization": 0.53242,
    "read_throughput": 12312.4324,
    "write_throughput": 3453.345,
    "average_wait": 30,
    "average_read_wait": 123,
    "average_write_wait": 90,
    "latency": 2,
    "read_latency": 3,
    "write_latency": 4,
    "queue_length": 123,
    "read_ql": 90,
    "write_ql": 781,
    "read_ios": 12379.435345,
    "write_ios": 8707809.98289,
    "x": 0,
    "y": 1,
}


def _compute_rates_single_disk(
    disk,
    value_store,
    value_store_suffix=".",
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
        "C:": DISK,
        "D:": DISK,
    }
    value_store: Dict[str, Any] = {}

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


@pytest.mark.parametrize(
    [
        "disks_to_combine",
        "expected_result",
    ],
    [
        pytest.param(
            [
                {
                    "a": 3,
                    "b": 3,
                },
                {
                    "a": 5.5345,
                    "c": 0.0,
                },
            ],
            {
                "a": 8.534500000000001,
                "b": 3.0,
                "c": 0.0,
            },
        ),
        pytest.param(
            [
                {
                    "a": 3,
                    "utilization": 3,
                    "latency": 5,
                    "read_latency": 5,
                    "write_latency": 6,
                },
                {
                    "a": 5.5345,
                    "c": 0.0,
                    "average_x": 0,
                    "latency": 1,
                    "read_latency": 2,
                    "write_latency": 3,
                },
                {
                    "a": 5.5345,
                    "utilization": 0.897878,
                },
                {
                    "average_x": 123.123123,
                    "average_y": 89,
                },
            ],
            {
                "a": 14.069000000000003,
                "average_x": 61.5615615,
                "average_y": 89.0,
                "c": 0.0,
                "latency": 3.0,
                "read_latency": 3.5,
                "utilization": 1.948939,
                "write_latency": 4.5,
            },
        ),
    ],
)
def test_combine_disks(
    disks_to_combine: Iterable[diskstat.Disk],
    expected_result: diskstat.Disk,
) -> None:
    assert diskstat.combine_disks(disks_to_combine) == expected_result


@pytest.mark.parametrize(
    [
        "disks_to_summarize",
        "expected_result",
    ],
    [
        pytest.param(
            [
                (
                    "disk1",
                    {
                        "a": 3,
                        "b": 3,
                    },
                ),
                (
                    "disk1",
                    {
                        "a": 5.5345,
                        "c": 0.0,
                    },
                ),
            ],
            {
                "a": 8.534500000000001,
                "b": 3.0,
                "c": 0.0,
            },
        ),
        pytest.param(
            [
                (
                    "disk1",
                    {
                        "a": 3,
                        "utilization": 3,
                        "latency": 5,
                        "read_latency": 5,
                        "write_latency": 6,
                    },
                ),
                (
                    "LVM 1",
                    {
                        "a": 5.5345,
                        "c": 0.0,
                        "average_x": 0,
                        "latency": 1,
                        "read_latency": 2,
                        "write_latency": 3,
                    },
                ),
                (
                    "disk2",
                    {
                        "a": 5.5345,
                        "utilization": 0.897878,
                    },
                ),
                (
                    "disk3",
                    {
                        "average_x": 123.123123,
                        "average_y": 89,
                    },
                ),
            ],
            {
                "a": 8.534500000000001,
                "average_x": 123.123123,
                "average_y": 89.0,
                "latency": 5.0,
                "read_latency": 5.0,
                "utilization": 1.948939,
                "write_latency": 6.0,
            },
        ),
    ],
)
def test_summarize_disks(
    disks_to_summarize: Iterable[Tuple[str, diskstat.Disk]],
    expected_result: diskstat.Disk,
) -> None:
    assert diskstat.summarize_disks(disks_to_summarize) == expected_result


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


LEVELS = {
    "horizon": 90,
    "levels_lower": ("absolute", (2.0, 4.0)),
    "levels_upper": ("absolute", (10.0, 20.0)),
    "levels_upper_min": (10.0, 15.0),
    "period": "wday",
}

LEVELS_SCALED = {
    "horizon": 90,
    "levels_lower": ("absolute", (20.0, 40.0)),
    "levels_upper": ("absolute", (100.0, 200.0)),
    "levels_upper_min": (100.0, 150.0),
    "period": "wday",
}


def test_scale_levels_predictive():
    assert diskstat._scale_levels_predictive(LEVELS, 10) == LEVELS_SCALED


def test_load_levels_wato():
    # when scaling the preditvie levels we make certain asumptions about the
    # wato structure of predictive levels here we try to make sure that these
    # asumptions are still correct. if this test fails, fix it and adapt
    # _scale_levels_predictive to handle the changed values
    from cmk.gui.plugins.wato.utils import PredictiveLevels

    pl = PredictiveLevels()
    pl.validate_value(LEVELS, "")
    pl.validate_datatype(LEVELS, "")


@pytest.mark.parametrize(
    "params,disk,exp_res",
    [
        (
            {},
            DISK,
            [
                Result(state=state.OK, notice="Utilization: 53.24%"),
                Metric("disk_utilization", 0.53242),
                Result(state=state.OK, summary="Read: 12.3 kB/s"),
                Metric("disk_read_throughput", 12312.4324),
                Result(state=state.OK, summary="Write: 3.45 kB/s"),
                Metric("disk_write_throughput", 3453.345),
                Result(state=state.OK, notice="Average wait: 30 seconds"),
                Metric("disk_average_wait", 30.0),
                Result(state=state.OK, notice="Average read wait: 2 minutes 3 seconds"),
                Metric("disk_average_read_wait", 123.0),
                Result(state=state.OK, notice="Average write wait: 1 minute 30 seconds"),
                Metric("disk_average_write_wait", 90.0),
                Result(state=state.OK, notice="Average queue length: 123.00"),
                Metric("disk_queue_length", 123.0),
                Result(state=state.OK, notice="Average read queue length: 90.00"),
                Metric("disk_read_ql", 90.0),
                Result(state=state.OK, notice="Average write queue length: 781.00"),
                Metric("disk_write_ql", 781.0),
                Result(state=state.OK, notice="Read operations: 12379.44/s"),
                Metric("disk_read_ios", 12379.435345),
                Result(state=state.OK, notice="Write operations: 8707809.98/s"),
                Metric("disk_write_ios", 8707809.98289),
                Result(state=state.OK, summary="Latency: 2 seconds"),
                Metric("disk_latency", 2.0),
                Result(state=state.OK, notice="Read latency: 3 seconds"),
                Metric("disk_read_latency", 3.0),
                Result(state=state.OK, notice="Write latency: 4 seconds"),
                Metric("disk_write_latency", 4.0),
                Metric("disk_x", 0.0),
                Metric("disk_y", 1.0),
            ],
        ),
        (
            (
                {
                    "utilization": (10, 20),
                    "read": (1e-5, 1e-4),
                    "write": (1e-5, 1e-4),
                    "latency": (1e3, 2e3),
                    "read_latency": (1e3, 2e3),
                    "write_latency": (1e3, 2e3),
                    "read_wait": (1e3, 2e3),
                    "write_wait": (1e3, 2e3),
                    "read_ios": (1e4, 1e5),
                    "write_ios": (1e5, 1e6),
                }
            ),
            DISK,
            [
                Result(state=state.CRIT, notice="Utilization: 53.24% (warn/crit at 10.00%/20.00%)"),
                Metric("disk_utilization", 0.53242, levels=(0.1, 0.2)),
                Result(state=state.CRIT, summary="Read: 12.3 kB/s (warn/crit at 10.0 B/s/100 B/s)"),
                Metric("disk_read_throughput", 12312.4324, levels=(10.0, 100.0)),
                Result(
                    state=state.CRIT,
                    summary="Write: 3.45 kB/s (warn/crit at 10.0 B/s/100 B/s)",
                ),
                Metric("disk_write_throughput", 3453.345, levels=(10.0, 100.0)),
                Result(state=state.OK, notice="Average wait: 30 seconds"),
                Metric("disk_average_wait", 30.0),
                Result(
                    state=state.CRIT,
                    notice="Average read wait: 2 minutes 3 seconds (warn/crit at 1 second/2 seconds)",
                ),
                Metric("disk_average_read_wait", 123.0, levels=(1.0, 2.0)),
                Result(
                    state=state.CRIT,
                    notice="Average write wait: 1 minute 30 seconds (warn/crit at 1 second/2 seconds)",
                ),
                Metric("disk_average_write_wait", 90.0, levels=(1.0, 2.0)),
                Result(state=state.OK, notice="Average queue length: 123.00"),
                Metric("disk_queue_length", 123.0),
                Result(state=state.OK, notice="Average read queue length: 90.00"),
                Metric("disk_read_ql", 90.0),
                Result(state=state.OK, notice="Average write queue length: 781.00"),
                Metric("disk_write_ql", 781.0),
                Result(
                    state=state.WARN,
                    notice="Read operations: 12379.44/s (warn/crit at 10000.00/s/100000.00/s)",
                ),
                Metric("disk_read_ios", 12379.435345, levels=(10000.0, 100000.0)),
                Result(
                    state=state.CRIT,
                    notice="Write operations: 8707809.98/s (warn/crit at 100000.00/s/1000000.00/s)",
                ),
                Metric("disk_write_ios", 8707809.98289, levels=(100000.0, 1000000.0)),
                Result(
                    state=state.CRIT,
                    summary="Latency: 2 seconds (warn/crit at 1 second/2 seconds)",
                ),
                Metric("disk_latency", 2.0, levels=(1.0, 2.0)),
                Result(
                    state=state.CRIT,
                    notice="Read latency: 3 seconds (warn/crit at 1 second/2 seconds)",
                ),
                Metric("disk_read_latency", 3.0, levels=(1.0, 2.0)),
                Result(
                    state=state.CRIT,
                    notice="Write latency: 4 seconds (warn/crit at 1 second/2 seconds)",
                ),
                Metric("disk_write_latency", 4.0, levels=(1.0, 2.0)),
                Metric("disk_x", 0.0),
                Metric("disk_y", 1.0),
            ],
        ),
        (
            {},
            {},
            [],
        ),
    ],
)
def test_check_diskstat_dict(params, disk, exp_res):
    exp_res = exp_res.copy()
    value_store: Dict[str, Any] = {}

    assert (
        list(
            diskstat.check_diskstat_dict(
                params=params, disk=disk, value_store=value_store, this_time=time.time()
            )
        )
        == exp_res
    )

    if exp_res:
        exp_res = [
            Result(state=state.OK, notice="All values averaged over 5 minutes 0 seconds"),
            *exp_res,
        ]

    assert (
        list(
            diskstat.check_diskstat_dict(
                params=({**params, "average": 300}),
                disk=disk,
                value_store=value_store,
                this_time=time.time(),
            ),
        )
        == exp_res
    )
