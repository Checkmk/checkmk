#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.base.plugins.agent_based import nfsiostat
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.nfsiostat import Section


@pytest.fixture(name="section1", scope="module")
def _section():
    return nfsiostat.parse_nfsiostat(
        [
            [
                "abcdef312-t2:/ifs/ic/abcdef_ticks",
                "mounted",
                "on",
                "/mnt/dubmdh_ticks:",
                "op/s",
                "rpc",
                "bklog",
                "1.66",
                "0.00",
                "read:",
                "ops/s",
                "kB/s",
                "kB/op",
                "retrans",
                "avg",
                "RTT",
                "(ms)",
                "avg",
                "exe",
                "(ms)",
                "0.276",
                "35.397",
                "128.271",
                "0",
                "(0.0%)",
                "11.251",
                "11.361",
                "write:",
                "ops/s",
                "kB/s",
                "kB/op",
                "retrans",
                "avg",
                "RTT",
                "(ms)",
                "avg",
                "exe",
                "(ms)",
                "0.000",
                "0.000",
                "0.000",
                "0",
                "(0.0%)",
                "0.000",
                "0.000",
            ]
        ]
    )


@pytest.fixture(name="section2", scope="module")
def _section2():
    return nfsiostat.parse_nfsiostat(
        [
            [
                "abcdef123-x01:/bud_win_redvol/root/Oracle/tnsnames",
                "mounted",
                "on",
                "/mnt/eu.abext.example.com/FOO/RedVol/Oracle/tnsnames:",
                "op/s",
                "rpc",
                "bklog",
                "1.24",
                "0.00",
                "read:",
                "ops/s",
                "kB/s",
                "kB/op",
                "retrans",
                "avg",
                "RTT",
                "(ms)",
                "avg",
                "exe",
                "(ms)",
                "0.000",
                "0.000",
                "19.605",
                "0",
                "(0.0%)",
                "0.690",
                "0.690",
                "write:",
                "ops/s",
                "kB/s",
                "kB/op",
                "retrans",
                "avg",
                "RTT",
                "(ms)",
                "avg",
                "exe",
                "(ms)",
                "0.000",
                "0.000",
                "0.000",
                "0",
                "(0.0%)",
                "0.000",
                "0.000",
            ]
        ]
    )


@pytest.mark.parametrize(
    "section, item",
    [
        pytest.param("section1", "'abcdef312-t2:/ifs/ic/abcdef_ticks',"),
        pytest.param("section2", "'abcdef123-x01:/bud_win_redvol/root/Oracle/tnsnames',"),
    ],
)
def test_item(section, item, request):
    services = list(nfsiostat.inventory_nfsiostat(request.getfixturevalue(section)))
    assert len(services) == 1
    assert services[0][0] == item


def test_nfsiostat_parse_old_nfsiostat_output(
    section1: Section,
) -> None:
    assert section1["'abcdef312-t2:/ifs/ic/abcdef_ticks',"] == tuple(
        [
            "1.66",
            "0.00",
            # read
            "0.276",
            "35.397",
            "128.271",
            "0",
            "0.0",
            "11.251",
            "11.361",
            # write
            "0.000",
            "0.000",
            "0.000",
            "0",
            "0.0",
            "0.000",
            "0.000",
        ]
    )


def test_nfsiostat_parse_newer_nfsiostat_output_format():
    # exe is the last value we report, avg queue and errors is not transported
    # read:  0.018 3 0.3 is not in the output
    # write: 0.077 4 0.4 is not in the output
    OUTPUT = (
        "host:/share mounted on /mount/point:"
        "ops/s rpc bklog"
        "3.909 1.234"
        "read: ops/s kB/s kB/op retrans avg RTT (ms) avg exe (ms) avg queue (ms) errors"
        "0.014 0.641 44.231 1 (0.1%) 0.900 0.927 0.018 3 (0.3%)"
        "write: ops/s kB/s kB/op retrans avg RTT (ms) avg exe (ms) avg queue (ms) errors"
        "0.082 5.133 62.228 2 (0.2%) 1.925 2.009 0.077 4 (0.4%)"
    )
    data_fix_mypy: tuple[str, ...] = (
        "3.909",
        "1.234",
        # read
        "0.014",
        "0.641",
        "44.231",
        "1",
        "0.1",
        "0.900",
        "0.927",
        # write
        "0.082",
        "5.133",
        "62.228",
        "2",
        "0.2",
        "1.925",
        "2.009",
    )

    assert nfsiostat.parse_nfsiostat([OUTPUT.split(" ")]) == {"'host:/share',": data_fix_mypy}


def test_nfsiostat_check(
    section1: Section,
) -> None:
    services = list(nfsiostat.inventory_nfsiostat(section1))
    item = services[0][0]
    assert isinstance(item, str)
    results = list(nfsiostat.check_nfsiostat(item=item, params={}, section=section1))
    assert results == [
        Result(state=State.OK, summary="Operations: 1.66/s"),
        Metric("op_s", 1.66),
        Result(state=State.OK, summary="RPC Backlog: 0.00"),
        Metric("rpc_backlog", 0.0),
        Result(state=State.OK, summary="Read operations /s: 0.276/s"),
        Metric("read_ops", 0.276),
        Result(state=State.OK, summary="Reads size /s: 35.397B/s"),
        Metric("read_b_s", 35.397),
        Result(state=State.OK, summary="Read bytes per operation: 128.271B/op"),
        Metric("read_b_op", 128.271),
        Result(state=State.OK, summary="Read Retransmission: 0.0%"),
        Metric("read_retrans", 0.0),
        Result(state=State.OK, summary="Read average RTT: 11.251/ms"),
        Metric("read_avg_rtt_ms", 11.251),
        Result(state=State.OK, summary="Read average EXE: 11.361/ms"),
        Metric("read_avg_exe_ms", 11.361),
        Result(state=State.OK, summary="Write operations /s: 0.000/s"),
        Metric("write_ops_s", 0.0),
        Result(state=State.OK, summary="Writes size /s: 0.000kB/s"),
        Metric("write_b_s", 0.0),
        Result(state=State.OK, summary="Write bytes per operation: 0.000B/op"),
        Metric("write_b_op", 0.0),
        Result(state=State.OK, summary="Write Retransmission: 0.000%"),
        Metric("write_retrans", 0.0),
        Result(state=State.OK, summary="Write Average RTT: 0.000/ms"),
        Metric("write_avg_rtt_ms", 0.0),
        Result(state=State.OK, summary="Write Average EXE: 0.000/ms"),
        Metric("write_avg_exe_ms", 0.0),
    ]


def test_nfsiostat_check2(
    section2: Section,
) -> None:
    services = list(nfsiostat.inventory_nfsiostat(section2))
    item = services[0][0]
    assert isinstance(item, str)
    results = list(nfsiostat.check_nfsiostat(item=item, params={}, section=section2))
    assert results == [
        Result(state=State.OK, summary="Operations: 1.24/s"),
        Metric("op_s", 1.24),
        Result(state=State.OK, summary="RPC Backlog: 0.00"),
        Metric("rpc_backlog", 0.0),
        Result(state=State.OK, summary="Read operations /s: 0.000/s"),
        Metric("read_ops", 0.0),
        Result(state=State.OK, summary="Reads size /s: 0.000B/s"),
        Metric("read_b_s", 0.0),
        Result(state=State.OK, summary="Read bytes per operation: 19.605B/op"),
        Metric("read_b_op", 19.605),
        Result(state=State.OK, summary="Read Retransmission: 0.0%"),
        Metric("read_retrans", 0.0),
        Result(state=State.OK, summary="Read average RTT: 0.690/ms"),
        Metric("read_avg_rtt_ms", 0.69),
        Result(state=State.OK, summary="Read average EXE: 0.690/ms"),
        Metric("read_avg_exe_ms", 0.69),
        Result(state=State.OK, summary="Write operations /s: 0.000/s"),
        Metric("write_ops_s", 0.0),
        Result(state=State.OK, summary="Writes size /s: 0.000kB/s"),
        Metric("write_b_s", 0.0),
        Result(state=State.OK, summary="Write bytes per operation: 0.000B/op"),
        Metric("write_b_op", 0.0),
        Result(state=State.OK, summary="Write Retransmission: 0.000%"),
        Metric("write_retrans", 0.0),
        Result(state=State.OK, summary="Write Average RTT: 0.000/ms"),
        Metric("write_avg_rtt_ms", 0.0),
        Result(state=State.OK, summary="Write Average EXE: 0.000/ms"),
        Metric("write_avg_exe_ms", 0.0),
    ]


def test_mount_name_ends_with_number():
    section = nfsiostat.parse_nfsiostat(
        [
            [
                "fsapp.zdv.uni-mainz.de:/seafile/024",
                "mounted",
                "on",
                "/fsapp/seafile_storage/024:",
                "ops/s",
                "rpc",
                "bklog",
                "730.890",
                "0.000",
                "read:",
                "ops/s",
                "kB/s",
                "kB/op",
                "retrans",
                "avg",
                "RTT",
                "(ms)",
                "avg",
                "exe",
                "(ms)",
                "2.622",
                "1.062",
                "0.405",
                "0",
                "(0.0%)",
                "1.137",
                "1.271",
                "write:",
                "ops/s",
                "kB/s",
                "kB/op",
                "retrans",
                "avg",
                "RTT",
                "(ms)",
                "avg",
                "exe",
                "(ms)",
                "0.000",
                "0.000",
                "0.000",
                "0",
                "(0.0%)",
                "0.000",
                "0.000",
            ]
        ]
    )

    services = list(nfsiostat.inventory_nfsiostat(section))
    item = services[0][0]
    assert isinstance(item, str)
    results = list(nfsiostat.check_nfsiostat(item=item, params={}, section=section))
    assert results[0] == Result(state=State.OK, summary="Operations: 730.89/s")


def test_mount_name_with_no_beginning_slash():
    section = nfsiostat.parse_nfsiostat(
        [
            [
                "10.61.241.85:ucs",
                "mounted",
                "on",
                "/home/thor/bkp:",
                "op/s",
                "rpc",
                "bklog",
                "0.54",
                "0.00",
                "read:",
                "ops/s",
                "kB/s",
                "kB/op",
                "retrans",
                "avg",
                "RTT",
                "(ms)",
                "avg",
                "exe",
                "(ms)",
                "0.000",
                "0.000",
                "0.000",
                "0",
                "(0.0%)",
                "0.000",
                "0.000",
                "write:",
                "ops/s",
                "kB/s",
                "kB/op",
                "retrans",
                "avg",
                "RTT",
                "(ms)",
                "avg",
                "exe",
                "(ms)",
                "0.389",
                "25.007",
                "64.278",
                "0",
                "(0.0%)",
                "13.013",
                "372.231",
            ]
        ]
    )

    services = list(nfsiostat.inventory_nfsiostat(section))
    item = services[0][0]
    assert item == "'10.61.241.85:ucs',"
    results = list(nfsiostat.check_nfsiostat(item=item, params={}, section=section))
    assert results[0] == Result(state=State.OK, summary="Operations: 0.54/s")
