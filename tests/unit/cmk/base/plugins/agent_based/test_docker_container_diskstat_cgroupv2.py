#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.api.agent_based.checking_classes import IgnoreResultsError
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.diskstat import check_diskstat
from cmk.base.plugins.agent_based.docker_container_diskstat_cgroupv2 import (
    parse_docker_container_diskstat_cgroupv2,
)
from cmk.base.plugins.agent_based.utils.df import FILESYSTEM_DEFAULT_LEVELS

AGENT_OUTPUT = """[time]
1614786439
[io.stat]
253:2 rbytes=4096 wbytes=49152 rios=1 wios=12 dbytes=0 dios=0
259:0 rbytes=7094272 wbytes=0 rios=353 wios=1 dbytes=0 dios=0
253:0 rbytes=7094272 wbytes=95592448 rios=353 wios=2166 dbytes=0 dios=0
253:1 rbytes=7090176 wbytes=95543296 rios=352 wios=2122 dbytes=0 dios=0
[names]
dm-0 253:0
dm-1 253:1
dm-2 253:2
loop0 7:0
loop1 7:1
loop10 7:10
loop11 7:11
loop2 7:2
loop3 7:3
loop4 7:4
loop5 7:5
loop6 7:6
loop7 7:7
loop8 7:8
loop9 7:9
nvme0n1 259:0
sda 8:0"""

AGENT_OUTPUT_0_SEC = """[time]
1614938883
[io.stat]
253:2 rbytes=434176 wbytes=4841472 rios=106 wios=1182 dbytes=0 dios=0
259:0 rbytes=559054848 wbytes=0 rios=3838 wios=8674730 dbytes=0 dios=0
253:0 rbytes=559054848 wbytes=292994383872 rios=3838 wios=6220665 dbytes=0 dios=0
253:1 rbytes=558620672 wbytes=292989542400 rios=3732 wios=6139289 dbytes=0 dios=0
[names]
dm-0 253:0
dm-1 253:1
dm-2 253:2
loop0 7:0
loop1 7:1
loop10 7:10
loop11 7:11
loop2 7:2
loop3 7:3
loop4 7:4
loop5 7:5
loop6 7:6
loop7 7:7
loop8 7:8
loop9 7:9
nvme0n1 259:0
sda 8:0"""

AGENT_OUTPUT_59_SEC = """[time]
1614938942
[io.stat]
253:2 rbytes=434176 wbytes=4841472 rios=106 wios=1182 dbytes=0 dios=0
259:0 rbytes=559349760 wbytes=0 rios=3910 wios=8674915 dbytes=0 dios=0
253:0 rbytes=559349760 wbytes=334268297216 rios=3910 wios=6265888 dbytes=0 dios=0
253:1 rbytes=558915584 wbytes=334263455744 rios=3804 wios=6158994 dbytes=0 dios=0
[names]
dm-0 253:0
dm-1 253:1
dm-2 253:2
loop0 7:0
loop1 7:1
loop10 7:10
loop11 7:11
loop2 7:2
loop3 7:3
loop4 7:4
loop5 7:5
loop6 7:6
loop7 7:7
loop8 7:8
loop9 7:9
nvme0n1 259:0
sda 8:0"""


def _split(string: str) -> StringTable:
    return [line.split(" ") for line in string.split("\n")]


def test_docker_container_diskstat_cgroupv2() -> None:
    with pytest.raises(IgnoreResultsError):
        # no rate metrics yet
        _ = list(
            check_diskstat(
                "nvme0n1",
                FILESYSTEM_DEFAULT_LEVELS,
                parse_docker_container_diskstat_cgroupv2(_split(AGENT_OUTPUT_0_SEC)),
                None,
            )
        )
    result = list(
        check_diskstat(
            "nvme0n1",
            FILESYSTEM_DEFAULT_LEVELS,
            parse_docker_container_diskstat_cgroupv2(_split(AGENT_OUTPUT_59_SEC)),
            None,
        )
    )

    assert result == [
        Result(state=State.OK, summary="Read: 5.00 kB/s"),
        Metric("disk_read_throughput", 4998.5084745762715),
        Result(state=State.OK, summary="Write: 0.00 B/s"),
        Metric("disk_write_throughput", 0.0),
        Result(state=State.OK, notice="Read operations: 1.22/s"),
        Metric("disk_read_ios", 1.2203389830508475),
        Result(state=State.OK, notice="Write operations: 3.14/s"),
        Metric("disk_write_ios", 3.135593220338983),
    ]


def test_parse_docker_container_diskstat_cgroupv2() -> None:
    string_table = _split(AGENT_OUTPUT)
    assert parse_docker_container_diskstat_cgroupv2(string_table) == {
        "dm-0": dict(
            read_ios=353,
            read_throughput=7094272,
            write_ios=2166,
            write_throughput=95592448,
            timestamp=1614786439,
        ),
        "dm-1": dict(
            read_ios=352,
            read_throughput=7090176,
            write_ios=2122,
            write_throughput=95543296,
            timestamp=1614786439,
        ),
        "dm-2": dict(
            read_ios=1,
            read_throughput=4096,
            write_ios=12,
            write_throughput=49152,
            timestamp=1614786439,
        ),
        "nvme0n1": dict(
            read_ios=353,
            read_throughput=7094272,
            write_ios=1,
            write_throughput=0,
            timestamp=1614786439,
        ),
    }
