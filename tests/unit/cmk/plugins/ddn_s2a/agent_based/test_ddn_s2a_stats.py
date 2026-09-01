#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.ddn_s2a.agent_based.ddn_s2a_stats import (
    check_ddn_s2a_stats,
    check_ddn_s2a_stats_io,
    check_ddn_s2a_stats_readhits,
    discover_ddn_s2a_stats,
    parse_ddn_s2a_stats,
)

_RESPONSE = (
    "0@30@All_ports_Read_MBs@30.0@Read_MBs@10.0@Read_MBs@20.0"
    "@All_ports_Write_MBs@6.0@Write_MBs@2.0@Write_MBs@4.0"
    "@All_ports_Read_IOs@300@Read_IOs@100@Read_IOs@200"
    "@All_ports_Write_IOs@60@Write_IOs@20@Write_IOs@40"
    "@All_ports_Read_Hits@99.4@Read_Hits@99.3@Read_Hits@99.5@$"
)

_SECTION = parse_ddn_s2a_stats([[_RESPONSE]])


def test_discover_ddn_s2a_stats() -> None:
    assert list(discover_ddn_s2a_stats(_SECTION)) == [
        Service(item="Total"),
        Service(item="1"),
        Service(item="2"),
    ]


def test_check_ddn_s2a_stats_readhits() -> None:
    assert list(check_ddn_s2a_stats_readhits("1", {"levels_lower": (85.0, 70.0)}, _SECTION)) == [
        Result(state=State.OK, summary="99.30%"),
        Metric("read_hits", 99.3),
    ]


def test_check_ddn_s2a_stats_readhits_below_levels() -> None:
    assert list(check_ddn_s2a_stats_readhits("2", {"levels_lower": (99.6, 99.0)}, _SECTION)) == [
        Result(state=State.WARN, summary="99.50% (warn/crit below 99.60%/99.00%)"),
        Metric("read_hits", 99.5),
    ]


def test_check_ddn_s2a_stats_io_total() -> None:
    assert list(check_ddn_s2a_stats_io("Total", {"total": (100.0, 200.0)}, _SECTION)) == [
        Result(state=State.OK, summary="Read: 300.00 1/s"),
        Metric("disk_read_ios", 300.0),
        Result(state=State.OK, summary="Write: 60.00 1/s"),
        Metric("disk_write_ios", 60.0),
        Result(state=State.CRIT, summary="Total: 360.00 1/s (warn/crit at 100.00/200.00 1/s)"),
    ]


def test_check_ddn_s2a_stats_datarate_per_port() -> None:
    # The levels are configured in bytes per second, but reported in MB/s.
    assert list(check_ddn_s2a_stats("1", {"total": (5 * 1024**2, 20 * 1024**2)}, _SECTION)) == [
        Result(state=State.OK, summary="Read: 10.00 MB/s"),
        Metric("disk_read_throughput", 10485760.0),
        Result(state=State.OK, summary="Write: 2.00 MB/s"),
        Metric("disk_write_throughput", 2097152.0),
        Result(state=State.WARN, summary="Total: 12.00 MB/s (warn/crit at 5.00/20.00 MB/s)"),
    ]


def test_check_ddn_s2a_stats_vanished_port() -> None:
    assert not list(check_ddn_s2a_stats("3", {}, _SECTION))
