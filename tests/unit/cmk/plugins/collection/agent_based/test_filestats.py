#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.base.legacy_checks.filestats import (
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
        ("aix agent files", {}),
        ("$ection with funny characters %s &! (count files in ~)", {}),
        ("log files", {}),
    ]


def test_discovery_single() -> None:
    section = parse_filestats(STRING_TABLE)
    assert list(discover_filestats_single(section)) == [
        ("file1.txt", {}),
        ("file2.txt", {}),
        ("file3.txt", {}),
        ("multiple-stats-per-single-service", {}),
    ]


@pytest.mark.parametrize(
    "item, params, expected",
    [
        (
            "aix agent files",
            {},
            [
                (0, "Files in total: 6", [("file_count", 6, None, None)]),
                (0, "Smallest: 1.15 kB", []),
                (0, "Largest: 12.9 kB", []),
                (0, "Newest: 2 days 15 hours", []),
                (0, "Oldest: 217 days 0 hours", []),
                (0, "\n"),
            ],
        ),
        (
            "aix agent files",
            {"maxsize_largest": (12 * 1024, 13 * 1024), "minage_newest": (3600 * 72, 3600 * 96)},
            [
                (0, "Files in total: 6", [("file_count", 6, None, None)]),
                (0, "Smallest: 1.15 kB", []),
                (1, "Largest: 12.9 kB (warn/crit at 12.3 kB/13.3 kB)", []),
                (2, "Newest: 2 days 15 hours (warn/crit below 3 days 0 hours/4 days 0 hours)", []),
                (0, "Oldest: 217 days 0 hours", []),
                (0, "\n"),
            ],
        ),
        (
            "$ection with funny characters %s &! (count files in ~)",
            {"maxcount": (5, 10)},
            [
                (
                    2,
                    "Files in total: 35819 (warn/crit at 5/10)",
                    [("file_count", 35819, 5, 10)],
                ),
            ],
        ),
        (
            "log files",
            {},
            [
                (0, "Files in total: 17", [("file_count", 17, None, None)]),
                (0, "Smallest: 0 B", []),
                (0, "Largest: 2.51 MB", []),
                (0, "Newest: 4 minutes 12 seconds", []),
                (0, "Oldest: 2 years 302 days", []),
                (0, "\n"),
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
                (0, "Size: 3.80 kB", [("size", 3804, None, None)]),
                (0, "Age: 14 hours 34 minutes", []),
            ],
        ),
        (
            "file2.txt",
            {"min_size": (2 * 1024, 1 * 1024), "max_size": (3 * 1024, 4 * 1024)},
            [
                (
                    1,
                    "Size: 3.80 kB (warn/crit at 3.07 kB/4.10 kB)",
                    [("size", 3804, 3072.0, 4096.0)],
                ),
                (0, "Age: 14 hours 34 minutes", []),
            ],
        ),
        (
            "file3.txt",
            {"min_age": (2 * 60, 1 * 60), "max_age": (3 * 60, 4 * 60)},
            [
                (0, "Size: 3.80 kB", [("size", 3804, None, None)]),
                (
                    2,
                    "Age: 14 hours 34 minutes (warn/crit at 3 minutes 0 seconds/4 minutes 0 seconds)",
                    [],
                ),
            ],
        ),
        (
            "multiple-stats-per-single-service",
            {},
            [
                (
                    1,
                    "Received multiple filestats per single file service. Please check agent "
                    "plug-in configuration (mk_filestats). For example, if there are multiple "
                    "non-utf-8 filenames, then they may be mapped to the same file service.",
                ),
                (0, "Size: 3.80 kB", [("size", 3804, None, None)]),
                (0, "Age: 14 hours 34 minutes", []),
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
        ["[[[single_file /�]]]"],
        ["{'type': 'file', 'path': '/�', 'stat_status': 'ok', 'size': 0, 'age': 87, 'mtime': 1}"],
        ["[[[single_file /�]]]"],
        ["{'type': 'file', 'path': '/�', 'stat_status': 'ok', 'size': 0, 'age': 111, 'mtime': 1}"],
    ]
    section = parse_filestats(string_table)
    results = list(check_filestats_single("/�", {}, section))
    assert results == [
        (
            1,
            "Received multiple filestats per single file service. Please check agent "
            "plug-in configuration (mk_filestats). For example, if there are multiple "
            "non-utf-8 filenames, then they may be mapped to the same file service.",
        ),
        (0, "Size: 0 B", [("size", 0, None, None)]),
        (0, "Age: 1 minute 27 seconds", []),
    ]
