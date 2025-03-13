#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import time
from collections.abc import Iterable, Mapping
from typing import Any
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import (
    CheckResult,
    get_rate,
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    State,
)
from cmk.plugins.lib import diskstat


@pytest.mark.parametrize(
    "params,exp_res",
    [
        (
            [
                {
                    "summary": True,
                    "lvm": False,
                    "vxvm": False,
                    "diskless": False,
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
                    "physical": "name",
                    "lvm": False,
                    "vxvm": False,
                    "diskless": False,
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
                    "physical": "wwn",  # This has no effect on discovery_diskstat_generic, see the diskstat plugin, if you need this functionality.
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
def test_discovery_diskstat_generic(params, exp_res) -> None:  # type: ignore[no-untyped-def]
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


def test_compute_rates_multiple_disks() -> None:
    disks = {
        "C:": DISK,
        "D:": DISK,
    }
    value_store: dict[str, Any] = {}

    # first call should result in IgnoreResultsError, second call should yield rates
    with time_machine.travel(datetime.datetime.fromtimestamp(0, tz=ZoneInfo("UTC"))):
        with pytest.raises(IgnoreResultsError):
            diskstat.compute_rates_multiple_disks(
                disks,
                value_store,
                _compute_rates_single_disk,
            )
    with time_machine.travel(datetime.datetime.fromtimestamp(60, tz=ZoneInfo("UTC"))):
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
    disks_to_summarize: Iterable[tuple[str, diskstat.Disk]],
    expected_result: diskstat.Disk,
) -> None:
    assert diskstat.summarize_disks(disks_to_summarize) == expected_result


@pytest.mark.parametrize(
    "params,disk,exp_res",
    [
        (
            {},
            DISK,
            [
                Result(state=State.OK, notice="Utilization: 53.24%"),
                Metric("disk_utilization", 0.53242),
                Result(state=State.OK, summary="Read: 12.3 kB/s"),
                Metric("disk_read_throughput", 12312.4324),
                Result(state=State.OK, summary="Write: 3.45 kB/s"),
                Metric("disk_write_throughput", 3453.345),
                Result(state=State.OK, notice="Average wait: 30 seconds"),
                Metric("disk_average_wait", 30.0),
                Result(state=State.OK, notice="Average read wait: 2 minutes 3 seconds"),
                Metric("disk_average_read_wait", 123.0),
                Result(state=State.OK, notice="Average write wait: 1 minute 30 seconds"),
                Metric("disk_average_write_wait", 90.0),
                Result(state=State.OK, notice="Average queue length: 123.00"),
                Metric("disk_queue_length", 123.0),
                Result(state=State.OK, notice="Average read queue length: 90.00"),
                Metric("disk_read_ql", 90.0),
                Result(state=State.OK, notice="Average write queue length: 781.00"),
                Metric("disk_write_ql", 781.0),
                Result(state=State.OK, notice="Read operations: 12379.44/s"),
                Metric("disk_read_ios", 12379.435345),
                Result(state=State.OK, notice="Write operations: 8707809.98/s"),
                Metric("disk_write_ios", 8707809.98289),
                Result(state=State.OK, summary="Latency: 2 seconds"),
                Metric("disk_latency", 2.0),
                Result(state=State.OK, notice="Read latency: 3 seconds"),
                Metric("disk_read_latency", 3.0),
                Result(state=State.OK, notice="Write latency: 4 seconds"),
                Metric("disk_write_latency", 4.0),
                Metric("disk_x", 0.0),
                Metric("disk_y", 1.0),
            ],
        ),
        (
            {
                "read_throughput": ("fixed", (10, 100)),
                "write_throughput": ("fixed", (10, 100)),
                "utilization": ("fixed", (0.1, 0.2)),
                "latency": ("fixed", (1.0, 2.0)),
                "read_latency": ("fixed", (1.0, 2.0)),
                "write_latency": ("fixed", (1.0, 2.0)),
                "average_read_wait": ("fixed", (1.0, 2.0)),
                "average_write_wait": ("fixed", (1.0, 2.0)),
                "read_ios": ("fixed", (10000.0, 100000.0)),
                "write_ios": ("fixed", (100000.0, 1000000.0)),
            },
            DISK,
            [
                Result(state=State.CRIT, notice="Utilization: 53.24% (warn/crit at 10.00%/20.00%)"),
                Metric("disk_utilization", 0.53242, levels=(0.1, 0.2)),
                Result(state=State.CRIT, summary="Read: 12.3 kB/s (warn/crit at 10.0 B/s/100 B/s)"),
                Metric("disk_read_throughput", 12312.4324, levels=(10.0, 100.0)),
                Result(
                    state=State.CRIT,
                    summary="Write: 3.45 kB/s (warn/crit at 10.0 B/s/100 B/s)",
                ),
                Metric("disk_write_throughput", 3453.345, levels=(10.0, 100.0)),
                Result(state=State.OK, notice="Average wait: 30 seconds"),
                Metric("disk_average_wait", 30.0),
                Result(
                    state=State.CRIT,
                    notice="Average read wait: 2 minutes 3 seconds (warn/crit at 1 second/2 seconds)",
                ),
                Metric("disk_average_read_wait", 123.0, levels=(1.0, 2.0)),
                Result(
                    state=State.CRIT,
                    notice="Average write wait: 1 minute 30 seconds (warn/crit at 1 second/2 seconds)",
                ),
                Metric("disk_average_write_wait", 90.0, levels=(1.0, 2.0)),
                Result(state=State.OK, notice="Average queue length: 123.00"),
                Metric("disk_queue_length", 123.0),
                Result(state=State.OK, notice="Average read queue length: 90.00"),
                Metric("disk_read_ql", 90.0),
                Result(state=State.OK, notice="Average write queue length: 781.00"),
                Metric("disk_write_ql", 781.0),
                Result(
                    state=State.WARN,
                    notice="Read operations: 12379.44/s (warn/crit at 10000.00/s/100000.00/s)",
                ),
                Metric("disk_read_ios", 12379.435345, levels=(10000.0, 100000.0)),
                Result(
                    state=State.CRIT,
                    notice="Write operations: 8707809.98/s (warn/crit at 100000.00/s/1000000.00/s)",
                ),
                Metric("disk_write_ios", 8707809.98289, levels=(100000.0, 1000000.0)),
                Result(
                    state=State.CRIT,
                    summary="Latency: 2 seconds (warn/crit at 1 second/2 seconds)",
                ),
                Metric("disk_latency", 2.0, levels=(1.0, 2.0)),
                Result(
                    state=State.CRIT,
                    notice="Read latency: 3 seconds (warn/crit at 1 second/2 seconds)",
                ),
                Metric("disk_read_latency", 3.0, levels=(1.0, 2.0)),
                Result(
                    state=State.CRIT,
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
def test_check_diskstat_dict(
    params: Mapping[str, object], disk: diskstat.Disk, exp_res: CheckResult
) -> None:
    value_store: dict[str, Any] = {}
    expected = list(exp_res)
    assert (
        list(
            diskstat.check_diskstat_dict_legacy(
                params=params,
                disk=disk,
                value_store=value_store,
                this_time=0.0,
            )
        )
        == expected
    )
    assert list(
        diskstat.check_diskstat_dict_legacy(
            params={**params, "average": 300},
            disk=disk,
            value_store=value_store,
            this_time=60.0,
        ),
    ) == [
        *(
            [Result(state=State.OK, notice="All values averaged over 5 minutes 0 seconds")]
            if expected
            else []
        ),
        *expected,
    ]
