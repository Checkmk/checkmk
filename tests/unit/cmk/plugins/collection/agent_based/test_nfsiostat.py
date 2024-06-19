#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.collection.agent_based import nfsiostat
from cmk.plugins.collection.agent_based.nfsiostat import Section


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
                "12.251",
                "12.361",
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
                "21.394",
                "13980.818",
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
    assert section1["'abcdef312-t2:/ifs/ic/abcdef_ticks',"] == nfsiostat.Mount(
        op_s=1.66,
        rpc_backlog=0.00,
        # read
        read_ops=0.276,
        read_b_s=35.397,
        read_b_op=128.271,
        read_retrans=0.0,
        read_avg_rtt_s=pytest.approx(0.012251),  # type: ignore[arg-type]
        read_avg_exe_s=pytest.approx(0.012361),  # type: ignore[arg-type]
        # write
        write_ops_s=0.000,
        write_b_s=0.000,
        write_b_op=0.000,
        write_retrans=0.0,
        write_avg_rtt_s=pytest.approx(0.021394),  # type: ignore[arg-type]
        write_avg_exe_s=pytest.approx(13.980818),  # type: ignore[arg-type]
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
    assert nfsiostat.parse_nfsiostat([OUTPUT.split(" ")]) == {
        "'host:/share',": nfsiostat.Mount(
            op_s=3.909,
            rpc_backlog=1.234,
            # read
            read_ops=0.014,
            read_b_s=0.641,
            read_b_op=44.231,
            read_retrans=0.1,
            read_avg_rtt_s=pytest.approx(0.000900),  # type: ignore[arg-type]
            read_avg_exe_s=pytest.approx(0.000927),  # type: ignore[arg-type]
            # write
            write_ops_s=0.082,
            write_b_s=5.133,
            write_b_op=62.228,
            write_retrans=0.2,
            write_avg_rtt_s=pytest.approx(0.001925),  # type: ignore[arg-type]
            write_avg_exe_s=pytest.approx(0.002009),  # type: ignore[arg-type]
        )
    }


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
        Result(state=State.OK, summary="Read operations: 0.28/s"),
        Metric("read_ops", 0.276),
        Result(state=State.OK, summary="Reads size: 35.4 B/s"),
        Metric("read_b_s", 35.397),
        Result(state=State.OK, summary="Read bytes per operation: 128.27 B/op"),
        Metric("read_b_op", 128.271),
        Result(state=State.OK, summary="Read Retransmission: 0%"),
        Metric("read_retrans", 0.0),
        Result(state=State.OK, summary="Read average RTT: 12 milliseconds"),
        Metric("read_avg_rtt_s", 0.012251),
        Result(state=State.OK, summary="Read average EXE: 12 milliseconds"),
        Metric("read_avg_exe_s", 0.012361),
        Result(state=State.OK, summary="Write operations: 0.00/s"),
        Metric("write_ops_s", 0.0),
        Result(state=State.OK, summary="Writes size: 0.00 B/s"),
        Metric("write_b_s", 0.0),
        Result(state=State.OK, summary="Write bytes per operation: 0.00 B/op"),
        Metric("write_b_op", 0.0),
        Result(state=State.OK, summary="Write Retransmission: 0%"),
        Metric("write_retrans", 0.0),
        Result(state=State.OK, summary="Write Average RTT: 21 milliseconds"),
        Metric("write_avg_rtt_s", 0.021394),
        Result(state=State.OK, summary="Write Average EXE: 14 seconds"),
        Metric("write_avg_exe_s", 13.980818),
    ]


def test_nfsiostat_check2(
    section1: Section,
) -> None:
    services = list(nfsiostat.inventory_nfsiostat(section1))
    item = services[0][0]
    assert isinstance(item, str)
    results = list(
        nfsiostat.check_nfsiostat(
            item=item,
            params={"write_avg_rtt_s": (0.01, 0.02), "write_avg_exe_s": (5.0, 20.0)},
            section=section1,
        )
    )
    assert results[-4:] == [
        Result(
            state=State.CRIT,
            summary="Write Average RTT: 21 milliseconds (warn/crit at 10 milliseconds/20 milliseconds)",
        ),
        Metric("write_avg_rtt_s", 0.021394, levels=(0.01, 0.02)),
        Result(
            state=State.WARN,
            summary="Write Average EXE: 14 seconds (warn/crit at 5 seconds/20 seconds)",
        ),
        Metric("write_avg_exe_s", 13.980818, levels=(5.0, 20.0)),
    ]


def test_nfsiostat_check3(
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
        Result(state=State.OK, summary="Read operations: 0.00/s"),
        Metric("read_ops", 0.0),
        Result(state=State.OK, summary="Reads size: 0.00 B/s"),
        Metric("read_b_s", 0.0),
        Result(state=State.OK, summary="Read bytes per operation: 19.61 B/op"),
        Metric("read_b_op", 19.605),
        Result(state=State.OK, summary="Read Retransmission: 0%"),
        Metric("read_retrans", 0.0),
        Result(state=State.OK, summary="Read average RTT: 690 microseconds"),
        Metric("read_avg_rtt_s", 0.00069),
        Result(state=State.OK, summary="Read average EXE: 690 microseconds"),
        Metric("read_avg_exe_s", 0.00069),
        Result(state=State.OK, summary="Write operations: 0.00/s"),
        Metric("write_ops_s", 0.0),
        Result(state=State.OK, summary="Writes size: 0.00 B/s"),
        Metric("write_b_s", 0.0),
        Result(state=State.OK, summary="Write bytes per operation: 0.00 B/op"),
        Metric("write_b_op", 0.0),
        Result(state=State.OK, summary="Write Retransmission: 0%"),
        Metric("write_retrans", 0.0),
        Result(state=State.OK, summary="Write Average RTT: 0 seconds"),
        Metric("write_avg_rtt_s", 0.0),
        Result(state=State.OK, summary="Write Average EXE: 0 seconds"),
        Metric("write_avg_exe_s", 0.0),
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
