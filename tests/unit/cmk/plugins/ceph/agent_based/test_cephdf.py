#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.ceph.agent_based.cephdf import (
    check_cephdf_testable,
    discover_cephdf,
    parse_cephdf,
    Section,
)
from cmk.plugins.lib import df

STRING_TABLE = [
    [
        '{"stats": {"total_bytes": 122903710400512, "total_avail_bytes": 88264260317184, '
        '"total_used_bytes": 34639450083328, "total_used_raw_bytes": 34639450083328, '
        '"total_used_raw_ratio": 0.2818421721458435, "num_osds": 16, "num_per_pool_osds": 16, '
        '"num_per_pool_omap_osds": 16}, "stats_by_class": {"nvme": {"total_bytes": '
        '122903710400512, "total_avail_bytes": 88264260317184, "total_used_bytes": '
        '34639450083328, "total_used_raw_bytes": 34639450083328, "total_used_raw_ratio": '
        '0.2818421721458435}}, "pools": [{"name": "nvme1", "id": 1, "stats": {"stored": '
        '11672967409291, "stored_data": 11672967184384, "stored_omap": 224907, "objects": '
        '3044978, "kb_used": 33686660127, "bytes_used": 34495139969953, "data_bytes_used": '
        '34495139295232, "omap_bytes_used": 674721, "percent_used": 0.3389628827571869, '
        '"max_avail": 22423858577408, "quota_objects": 0, "quota_bytes": 0, "dirty": 0, "rd": '
        '61744664209, "rd_bytes": 4798695416181760, "wr": 137785316968, "wr_bytes": '
        '3083978441281536, "compress_bytes_used": 0, "compress_under_bytes": 0, "stored_raw": '
        '35018902601728, "avail_raw": 67271574686528}}, {"name": ".mgr", "id": 2, "stats": '
        '{"stored": 19727088, "stored_data": 19727088, "stored_omap": 0, "objects": 6, "kb_used": '
        '57804, "bytes_used": 59191296, "data_bytes_used": 59191296, "omap_bytes_used": 0, '
        '"percent_used": 8.798849648883333e-07, "max_avail": 22423858577408, "quota_objects": 0, '
        '"quota_bytes": 0, "dirty": 0, "rd": 84182, "rd_bytes": 142103552, "wr": 170979, '
        '"wr_bytes": 3919172608, "compress_bytes_used": 0, "compress_under_bytes": 0, '
        '"stored_raw": 59181264, "avail_raw": 67271574686528}}]}'
    ]
]


def _section() -> Section:
    assert (section := parse_cephdf(STRING_TABLE)) is not None
    return section


def test_discovery() -> None:
    assert list(discover_cephdf(_section())) == [Service(item="nvme1"), Service(item=".mgr")]


def test_check_not_found() -> None:
    assert not list(check_cephdf_testable("no-such-item", {}, _section(), 0, {}))


def test_check_found() -> None:
    now = 1719984586
    value_store = {
        "nvme1.delta": (now - 60, 0),
        "nvme1.ri": (now - 60, 0),
        "nvme1.wi": (now - 60, 0),
        "nvme1.rb": (now - 60, 0),
        "nvme1.wb": (now - 60, 0),
    }
    assert list(
        check_cephdf_testable("nvme1", df.FILESYSTEM_DEFAULT_PARAMS, _section(), now, value_store)
    ) == [
        # unrealistic numbers due to the tests value store initialization
        Metric(
            "fs_used",
            11132209.21448803,
            levels=(26013813.771590233, 29265540.49303913),
            boundaries=(0.0, 32517267.21448803),
        ),
        Metric("fs_free", 21385058.0, boundaries=(0.0, None)),
        Metric(
            "fs_used_percent",
            34.23476253726539,
            levels=(79.99999999999942, 89.9999999999997),
            boundaries=(0.0, 100.0),
        ),
        Result(state=State.OK, summary="Used: 34.23% - 10.6 TiB of 31.0 TiB"),
        Metric("fs_size", 32517267.21448803, boundaries=(0.0, None)),
        Metric("growth", 16030381268.862762),
        Result(state=State.OK, summary="trend per 1 day 0 hours: +14.9 PiB"),
        Result(state=State.OK, summary="trend per 1 day 0 hours: +49298.06%"),
        Metric("trend", 16030381268.862762),
        Result(state=State.OK, summary="Time left until disk full: 1 minute 55 seconds"),
        Result(state=State.OK, summary="Objects: 3044978.00"),
        Metric("num_objects", 3044978.0),
        Result(state=State.OK, summary="Read IOPS: 1029077736.82"),
        Metric("disk_read_ios", 1029077736.8166667),
        Result(state=State.OK, summary="Write IOPS: 2296421949.47"),
        Metric("disk_write_ios", 2296421949.4666667),
        Result(state=State.OK, summary="Read Throughput: 72.7 TiB"),
        Metric("disk_read_throughput", 79978256936362.67),
        Result(state=State.OK, summary="Write Throughput: 46.7 TiB"),
        Metric("disk_write_throughput", 51399640688025.6),
    ]
