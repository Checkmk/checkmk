#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.collection.agent_based.diskstat_io import _check_diskstat_io
from cmk.plugins.collection.agent_based.hpux_lunstats import parse_hpux_lunstats
from cmk.plugins.lib.diskstat import discovery_diskstat_generic, Section

STRING_TABLE = [
    ["WWID", "  0x5000cca00b045e9c"],
    ["	STATISTICS FOR LUN ", "/dev/rdisk/disk4"],
    ["Bytes read                                       ", " 16375049"],
    ["Bytes written                                    ", " 571040768"],
    ["Total I/Os processed                             ", " 870553"],
    ["I/O failures                                     ", " 0"],
    ["Retried I/O failures                             ", " 0"],
    ["I/O failures due to invalid IO size              ", " 0"],
    ["WWID", "  0x5000c50013801e7f"],
    ["	STATISTICS FOR LUN ", "/dev/rdisk/disk5"],
    ["Bytes read                                       ", " 229698466718"],
    ["Bytes written                                    ", " 458434521088"],
    ["Total I/Os processed                             ", " 67841911"],
    ["I/O failures                                     ", " 0"],
    ["Retried I/O failures                             ", " 0"],
    ["I/O failures due to invalid IO size              ", " 0"],
    ["WWID", "  0x60a98000572d447456346450776b4c67"],
    ["	STATISTICS FOR LUN ", "/dev/rdisk/disk20"],
    ["Bytes read                                       ", " 66875865358"],
    ["Bytes written                                    ", " 27759884288"],
    ["Total I/Os processed                             ", " 6483391"],
    ["I/O failures                                     ", " 18"],
    ["Retried I/O failures                             ", " 0"],
    ["I/O failures due to invalid IO size              ", " 0"],
    ["WWID", "  0x60a98000572d44745634645077717449"],
    ["	STATISTICS FOR LUN ", "/dev/rdisk/disk21"],
    ["Bytes read                                       ", " 2760640735497"],
    ["Bytes written                                    ", " 549730951168"],
    ["Total I/Os processed                             ", " 68172495"],
    ["I/O failures                                     ", " 33"],
    ["Retried I/O failures                             ", " 0"],
    ["I/O failures due to invalid IO size              ", " 0"],
    ["WWID", "  0x60a98000572d447456346450774a6948"],
    ["	STATISTICS FOR LUN ", "/dev/rdisk/disk22"],
    ["Bytes read                                       ", " 2859709547785"],
    ["Bytes written                                    ", " 514804342784"],
    ["Total I/Os processed                             ", " 84900754"],
    ["I/O failures                                     ", " 37"],
    ["Retried I/O failures                             ", " 0"],
    ["I/O failures due to invalid IO size              ", " 0"],
    ["WWID", "  0x60a98000572d44745634645077625679"],
    ["	STATISTICS FOR LUN ", "/dev/rdisk/disk23"],
    ["Bytes read                                       ", " 251929835785"],
    ["Bytes written                                    ", " 171925457920"],
    ["Total I/Os processed                             ", " 23209476"],
    ["I/O failures                                     ", " 24"],
    ["Retried I/O failures                             ", " 0"],
    ["I/O failures due to invalid IO size              ", " 0"],
]


@pytest.fixture(scope="module", name="section")
def _get_section() -> Section:
    return parse_hpux_lunstats(STRING_TABLE)


def test_discover_default(section: Section) -> None:
    assert list(
        discovery_diskstat_generic(
            [{"summary": True, "physical": {}, "lvm": False, "vxvm": False, "diskless": False}],
            section,
        )
    ) == [
        Service(item="SUMMARY"),
    ]


def test_discover_physical(section: Section) -> None:
    assert list(
        discovery_diskstat_generic(
            [
                {
                    "summary": False,
                    "physical": {"service_name": "name"},
                    "lvm": False,
                    "vxvm": False,
                    "diskless": False,
                }
            ],
            section,
        )
    ) == [
        Service(item="/dev/rdisk/disk4"),
        Service(item="/dev/rdisk/disk5"),
        Service(item="/dev/rdisk/disk20"),
        Service(item="/dev/rdisk/disk21"),
        Service(item="/dev/rdisk/disk22"),
        Service(item="/dev/rdisk/disk23"),
    ]


def test_check_hpux_lunstats_not_found(section: Section) -> None:
    assert not list(_check_diskstat_io("möööööööp", {}, section, {}, 0.0))


def test_check_hpux_lunstats_summary(section: Section) -> None:
    vs = {
        "write_throughput": (1659105408, 3360676168),
        "read_throughput": (1659105408, 12040575829),
    }
    this_time = 1659105468
    assert list(
        _check_diskstat_io(
            "SUMMARY",
            {"summary": False, "physical": {}, "lvm": False, "vxvm": False, "diskless": False},
            section,
            vs,
            this_time,
        )
    ) == [
        Result(
            state=State.OK,
            summary="Read: 103 GB/s",  # <- wow :-)
        ),
        Metric("disk_read_throughput", 102613837506.05),
        Result(
            state=State.OK,
            summary="Write: 28.7 GB/s",
        ),
        Metric("disk_write_throughput", 28664425364.133335),
    ]


def test_check_hpux_lunstats(section: Section) -> None:
    read_test_data = 2760640735497
    write_test_data = 549730951168
    item = "/dev/rdisk/disk21"

    now = 1659105468
    vs = {
        "write_throughput": (now - 60, (write_test_data - 1000**2 * 60)),
        "read_throughput": (now - 60, (read_test_data - 1024**2 * 60)),
    }
    assert list(_check_diskstat_io(item, {}, section, vs, now)) == [
        Result(
            state=State.OK,
            summary="Read: 1.05 MB/s",
        ),
        Metric("disk_read_throughput", 1048576.0),
        Result(
            state=State.OK,
            summary="Write: 1.00 MB/s",
        ),
        Metric("disk_write_throughput", 1000000.0),
    ]
