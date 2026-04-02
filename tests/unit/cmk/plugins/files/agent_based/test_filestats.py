#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-def"


import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.files.agent_based.filestats import (
    check_filestats,
    check_filestats_single,
    discover_filestats,
    discover_filestats_single,
    parse_filestats,
)

STRING_TABLE = [
    ["[[[file_stats aix agent files]]]"],
    [
        "{'stat_status': 'ok', 'age': 230276, 'mtime': 1544196317,"
        " 'path': '/home/mo/git/check_mk/agents/check_mk_agent.aix', 'type': 'file', 'size': 12886}"
    ],
    [
        "{'stat_status': 'ok', 'age': 18751603, 'mtime': 1525674990,"
        " 'path': '/home/mo/git/check_mk/agents/plugins/mk_sap.aix', 'type': 'file', 'size': 3928}"
    ],
    [
        "{'stat_status': 'ok', 'age': 230276, 'mtime': 1544196317, 'path':"
        " '/home/mo/git/check_mk/agents/plugins/mk_logwatch.aix', 'type': 'file', 'size': 1145}"
    ],
    [
        "{'stat_status': 'ok', 'age': 18751603, 'mtime': 1525674990, 'path':"
        " '/home/mo/git/check_mk/agents/plugins/netstat.aix', 'type': 'file', 'size': 1697}"
    ],
    [
        "{'stat_status': 'ok', 'age': 9398016, 'mtime': 1535028577, 'path':"
        " '/home/mo/git/check_mk/agents/plugins/mk_inventory.aix', 'type': 'file', 'size': 2637}"
    ],
    [
        "{'stat_status': 'ok', 'age': 18751603, 'mtime': 1525674990, 'path':"
        " '/home/mo/git/check_mk/agents/plugins/mk_db2.aix', 'type': 'file', 'size': 10138}"
    ],
    ["{'type': 'summary', 'count': 6}"],
    ["[[[count_only $ection with funny characters %s &! (count files in ~)]]]"],
    ["{'type': 'summary', 'count': 35819}"],
    ["[[[extremes_only log files]]]"],
    [
        "{'stat_status': 'ok', 'age': 89217820, 'mtime': 1455208773, 'path':"
        " '/var/log/installer/casper.log', 'type': 'file', 'size': 1216}"
    ],
    [
        "{'stat_status': 'ok', 'age': 4451, 'mtime': 1544422142, 'path': '/var/log/boot.log',"
        " 'type': 'file', 'size': 2513750}"
    ],
    [
        "{'stat_status': 'ok', 'age': 252, 'mtime': 1544426341, 'path': '/var/log/auth.log',"
        " 'type': 'file', 'size': 7288}"
    ],
    [
        "{'stat_status': 'ok', 'age': 15965608, 'mtime': 1528460985, 'path': '/var/log/tacwho.log',"
        " 'type': 'file', 'size': 0}"
    ],
    ["{'type': 'summary', 'count': 17}"],
    ["[[[single_file file1.txt]]]"],
    [
        "{'stat_status': 'ok', 'age': 52456, 'mtime': 1583771842, 'path': u'/home/file1.txt', 'type': 'file', 'size': 3804}"
    ],
    ["[[[single_file file2.txt]]]"],
    [
        "{'stat_status': 'ok', 'age': 52456, 'mtime': 1583771842, 'path': u'/home/file2.txt', 'type': 'file', 'size': 3804}"
    ],
    ["[[[single_file file3.txt]]]"],
    [
        "{'stat_status': 'ok', 'age': 52456, 'mtime': 1583771842, 'path': u'/home/file3.txt', 'type': 'file', 'size': 3804}"
    ],
    ["[[[single_file multiple-stats-per-single-service]]]"],
    [
        "{'stat_status': 'ok', 'age': 52456, 'mtime': 1583771842, 'path': u'/home/file3.txt', 'type': 'file', 'size': 3804}"
    ],
    [
        "{'stat_status': 'ok', 'age': 52456, 'mtime': 1583771842, 'path': u'/home/file3.txt', 'type': 'file', 'size': 3804}"
    ],
]


def test_discovery() -> None:
    section = parse_filestats(STRING_TABLE)
    assert list(discover_filestats(section)) == [
        Service(item="aix agent files"),
        Service(item="$ection with funny characters %s &! (count files in ~)"),
        Service(item="log files"),
    ]


def test_discovery_single() -> None:
    section = parse_filestats(STRING_TABLE)
    assert list(discover_filestats_single(section)) == [
        Service(item="file1.txt"),
        Service(item="file2.txt"),
        Service(item="file3.txt"),
        Service(item="multiple-stats-per-single-service"),
    ]


@pytest.mark.parametrize(
    "item, params, expected",
    [
        (
            "aix agent files",
            {},
            [
                Result(state=State.OK, summary="Files in total: 6"),
                Metric("file_count", 6.0),
                Result(state=State.OK, summary="Smallest: 1.15 kB"),
                Result(state=State.OK, summary="Largest: 12.9 kB"),
                Result(state=State.OK, summary="Newest: 2 days 15 hours"),
                Result(state=State.OK, summary="Oldest: 217 days 0 hours"),
            ],
        ),
        (
            "aix agent files",
            {"maxsize_largest": (12 * 1024, 13 * 1024), "minage_newest": (3600 * 72, 3600 * 96)},
            [
                Result(state=State.OK, summary="Files in total: 6"),
                Metric("file_count", 6.0),
                Result(state=State.OK, summary="Smallest: 1.15 kB"),
                Result(state=State.WARN, summary="Largest: 12.9 kB (warn/crit at 12.3 kB/13.3 kB)"),
                Result(
                    state=State.CRIT,
                    summary="Newest: 2 days 15 hours (warn/crit below 3 days 0 hours/4 days 0 hours)",
                ),
                Result(state=State.OK, summary="Oldest: 217 days 0 hours"),
            ],
        ),
        (
            "$ection with funny characters %s &! (count files in ~)",
            {"maxcount": (5, 10)},
            [
                Result(state=State.CRIT, summary="Files in total: 35819 (warn/crit at 5/10)"),
                Metric("file_count", 35819.0, levels=(5.0, 10.0)),
            ],
        ),
        (
            "log files",
            {},
            [
                Result(state=State.OK, summary="Files in total: 17"),
                Metric("file_count", 17.0),
                Result(state=State.OK, summary="Smallest: 0 B"),
                Result(state=State.OK, summary="Largest: 2.51 MB"),
                Result(state=State.OK, summary="Newest: 4 minutes 12 seconds"),
                Result(state=State.OK, summary="Oldest: 2 years 302 days"),
            ],
        ),
    ],
)
def test_check_regression(item, params, expected):
    section = parse_filestats(STRING_TABLE)
    results = list(check_filestats(item, params, section))
    assert results == expected


@pytest.mark.parametrize(
    "item, params, expected",
    [
        (
            "file1.txt",
            {},
            [
                Result(state=State.OK, summary="Size: 3.80 kB"),
                Metric("size", 3804.0),
                Result(state=State.OK, summary="Age: 14 hours 34 minutes"),
            ],
        ),
        (
            "file2.txt",
            {"min_size": (2 * 1024, 1 * 1024), "max_size": (3 * 1024, 4 * 1024)},
            [
                Result(state=State.WARN, summary="Size: 3.80 kB (warn/crit at 3.07 kB/4.10 kB)"),
                Metric("size", 3804.0, levels=(3072.0, 4096.0)),
                Result(state=State.OK, summary="Age: 14 hours 34 minutes"),
            ],
        ),
        (
            "file3.txt",
            {"min_age": (2 * 60, 1 * 60), "max_age": (3 * 60, 4 * 60)},
            [
                Result(state=State.OK, summary="Size: 3.80 kB"),
                Metric("size", 3804.0),
                Result(
                    state=State.CRIT,
                    summary="Age: 14 hours 34 minutes (warn/crit at 3 minutes 0 seconds/4 minutes 0 seconds)",
                ),
            ],
        ),
        (
            "multiple-stats-per-single-service",
            {},
            [
                Result(
                    state=State.WARN,
                    summary="Received multiple filestats per single file service. Please check agent "
                    "plug-in configuration (mk_filestats). For example, if there are multiple "
                    "non-utf-8 filenames, then they may be mapped to the same file service.",
                ),
                Result(state=State.OK, summary="Size: 3.80 kB"),
                Metric("size", 3804.0),
                Result(state=State.OK, summary="Age: 14 hours 34 minutes"),
            ],
        ),
    ],
)
def test_check_single_regression(item, params, expected):
    section = parse_filestats(STRING_TABLE)
    results = list(check_filestats_single(item, params, section))
    assert results == expected


def test_check_single_duplicate_file() -> None:
    """Data as the one below occurs due to Werk 15605. However, since the behaviour below was not
    introduced by that Werk, such data may occur in other situations as well."""
    string_table = [
        ["[[[single_file /\ufffd]]]"],
        [
            "{'type': 'file', 'path': '/\ufffd', 'stat_status': 'ok', 'size': 0, 'age': 87, 'mtime': 1}"
        ],
        ["[[[single_file /\ufffd]]]"],
        [
            "{'type': 'file', 'path': '/\ufffd', 'stat_status': 'ok', 'size': 0, 'age': 111, 'mtime': 1}"
        ],
    ]
    section = parse_filestats(string_table)
    results = list(check_filestats_single("/\ufffd", {}, section))
    assert results == [
        Result(
            state=State.WARN,
            summary="Received multiple filestats per single file service. Please check agent "
            "plug-in configuration (mk_filestats). For example, if there are multiple "
            "non-utf-8 filenames, then they may be mapped to the same file service.",
        ),
        Result(state=State.OK, summary="Size: 0 B"),
        Metric("size", 0.0),
        Result(state=State.OK, summary="Age: 1 minute 27 seconds"),
    ]
