#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Mapping
from copy import deepcopy
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.collection.agent_based import fileinfo as fileinfo_plugin
from cmk.plugins.lib import fileinfo as fileinfo_utils
from cmk.plugins.lib.fileinfo import (
    discovery_fileinfo_groups,
    DiscoveryParams,
    Fileinfo,
    FileinfoItem,
)

INFO = [
    ["1563288717"],
    ["[[[header]]]"],
    ["name", "status", "size", "time"],
    ["[[[content]]]"],
    ["/var/log/syslog", "ok", "1307632", "1563288713"],
    ["/var/log/syslog.1", "ok", "1235157", "1563259976"],
    ["/var/log/aptitude", "ok", "0", "1543826115"],
    ["/var/log/aptitude.2.gz", "ok", "3234", "1539086721"],
    ["/tmp/20190716.txt", "ok", "1235157", "1563259976"],
]
INFO_MISSING_TIME_SYSLOG = deepcopy(INFO)
INFO_MISSING_TIME_SYSLOG[4][3] = ""


def test_fileinfo_min_max_age_levels() -> None:
    # This test has the following purpose:
    # For each file attr (size or age) the levels 'min*', 'max*' are evaluated.
    # 'min*' is evaluated first and if 'max*' returns state '0' (eg. not set)
    # the service state is also '0'.

    item = "c:\\filetest\\check_mk.txt"
    parsed = fileinfo_utils.parse_fileinfo(
        [
            ["8"],
            ["c:\\filetest\\check_mk.txt", "7", "5"],
        ]
    )

    size_result = [Result(state=State.OK, summary="Size: 7 B"), Metric("size", 7.0)]

    # minage matches
    output_minage = fileinfo_plugin.check_fileinfo(
        item,
        {
            "minage": (5, 1),
        },
        parsed,
    )

    # In 1.6.0 warn, crit of minage was added, but now we use the
    # generic check_levels function.

    assert list(output_minage) == size_result + [
        Result(state=State.WARN, summary="Age: 3 seconds (warn/crit below 5 seconds/1 second)"),
        Metric("age", 3.0),
    ]

    # maxage matches
    output_maxage = fileinfo_plugin.check_fileinfo(
        item,
        {
            "maxage": (1, 2),
        },
        parsed,
    )

    assert list(output_maxage) == size_result + [
        Result(state=State.CRIT, summary="Age: 3 seconds (warn/crit at 1 second/2 seconds)"),
        Metric("age", 3.0, levels=(1.0, 2.0)),
    ]

    # both match
    # This should never happen (misconfiguration), but test the order
    # of min* vs. max* and perfdata (always take the upper levels)
    # In 1.6.0 levels text of minage was added, but now we use the
    # generic check_levels function.
    output_both = fileinfo_plugin.check_fileinfo(
        item,
        {
            "minage": (5, 1),
            "maxage": (1, 2),
        },
        parsed,
    )

    assert list(output_both) == size_result + [
        Result(state=State.CRIT, summary="Age: 3 seconds (warn/crit at 1 second/2 seconds)"),
        Metric("age", 3.0, levels=(1.0, 2.0)),
    ]


@pytest.mark.parametrize(
    "info, parsed, discovery_params, expected_result",
    [
        (
            [
                # legacy format
                ["1563288717"],
                ["[[[header]]]"],
                ["name", "status", "size", "time"],
            ],
            Fileinfo(
                reftime=1563288717,
                files={},
            ),
            [{"group_patterns": [("banana", ("/banana/*", ""))]}],
            [
                Result(state=State.OK, notice="Include patterns: /banana/*"),
                Result(state=State.OK, summary="Count: 0"),
                Metric("count", 0),
                Result(state=State.OK, summary="Size: 0 B"),
                Metric("size", 0),
            ],
        ),
        (
            [],
            Fileinfo(),
            [{"group_patterns": []}],
            [
                Result(state=State.UNKNOWN, summary="Missing reference timestamp"),
            ],
        ),
        (
            [
                ["1563288717"],
            ],
            Fileinfo(
                reftime=1563288717,
                files={},
            ),
            [{"group_patterns": [("banana", ("/banana/*", ""))]}],
            [
                Result(state=State.OK, notice="Include patterns: /banana/*"),
                Result(state=State.OK, summary="Count: 0"),
                Metric("count", 0),
                Result(state=State.OK, summary="Size: 0 B"),
                Metric("size", 0),
            ],
        ),
    ],
)
def test_check_fileinfo_group_no_files(
    info: StringTable,
    parsed: Fileinfo,
    discovery_params: DiscoveryParams,
    expected_result: CheckResult,
) -> None:
    """Test that the check returns an OK status when there are no files."""
    assert fileinfo_utils.parse_fileinfo(info) == parsed
    assert not list(discovery_fileinfo_groups(discovery_params, parsed))
    assert expected_result == list(
        fileinfo_plugin.check_fileinfo_groups(
            "banana",
            {"group_patterns": [("/banana/*", "")]},
            parsed,
        )
    )


@pytest.mark.parametrize(
    "info, parsed, expected_result",
    [
        (
            [
                # legacy format
                ["1563288717"],
                ["[[[header]]]"],
                ["name", "status", "size", "time"],
                ["[[[content]]]"],
                ["/bar/foo", "ok", "384", "1465079135"],
                ["/foo/bar", "ok", "384", "1465079135"],
            ],
            Fileinfo(
                reftime=1563288717,
                files={
                    "/bar/foo": FileinfoItem(
                        name="/bar/foo", missing=False, failed=False, size=348, time=1465079135
                    ),
                    "/foo/bar": FileinfoItem(
                        name="/foo/bar", missing=False, failed=False, size=348, time=1465079135
                    ),
                },
            ),
            [
                Result(state=State.OK, notice="Include patterns: /banana/*"),
                Result(state=State.OK, summary="Count: 0"),
                Metric("count", 0),
                Result(state=State.OK, summary="Size: 0 B"),
                Metric("size", 0),
            ],
        ),
        (
            [
                ["1563288717"],
                ["/bar/foo", "384", "1465079135"],
                ["/foo/bar", "384", "1465079135"],
            ],
            Fileinfo(
                reftime=1563288717,
                files={
                    "/bar/foo": FileinfoItem(
                        name="/bar/foo", missing=False, failed=False, size=348, time=1465079135
                    ),
                    "/foo/bar": FileinfoItem(
                        name="/foo/bar", missing=False, failed=False, size=348, time=1465079135
                    ),
                },
            ),
            [
                Result(state=State.OK, notice="Include patterns: /banana/*"),
                Result(state=State.OK, summary="Count: 0"),
                Metric("count", 0),
                Result(state=State.OK, summary="Size: 0 B"),
                Metric("size", 0),
            ],
        ),
    ],
)
def test_check_fileinfo_group_no_matching_files(
    info: StringTable,
    parsed: Fileinfo,
    expected_result: CheckResult,
) -> None:
    """Test that the check returns an OK status if there are no matching files."""

    actual_parsed = fileinfo_utils.parse_fileinfo(info)
    assert parsed.reftime == actual_parsed.reftime
    assert list(parsed.files) == list(actual_parsed.files)
    assert expected_result == list(
        fileinfo_plugin.check_fileinfo_groups(
            "banana",
            {"group_patterns": [("/banana/*", "")]},
            parsed,
        )
    )


@pytest.mark.parametrize(
    "info, group_pattern, expected_result",
    [
        (
            [
                ["1563288717"],
                ["/var/log/syslog", "384", "1465079135"],
                ["/var/log/syslog1", "384", "1465079135"],
            ],
            {
                # current format
                "group_patterns": [("/var/log/sys*", "")]
            },
            [
                Result(state=State.OK, notice="Include patterns: /var/log/sys*"),
                Result(
                    state=State.OK, notice="[/var/log/syslog] Age: 3 years 41 days, Size: 384 B"
                ),
                Result(
                    state=State.OK, notice="[/var/log/syslog1] Age: 3 years 41 days, Size: 384 B"
                ),
                Result(state=State.OK, summary="Count: 2"),
                Metric("count", 2),
                Result(state=State.OK, summary="Size: 768 B"),
                Metric("size", 768),
                Result(state=State.OK, summary="Largest size: 384 B"),
                Metric("size_largest", 384),
                Result(state=State.OK, summary="Smallest size: 384 B"),
                Metric("size_smallest", 384),
                Result(state=State.OK, summary="Oldest age: 3 years 41 days"),
                Metric("age_oldest", 98209582),
                Result(state=State.OK, summary="Newest age: 3 years 41 days"),
                Metric("age_newest", 98209582),
            ],
        ),
        (
            [
                ["1563288717"],
                ["/var/log/syslog", "384", "1465079135"],
                ["/var/log/syslog1", "384", "1465079135"],
            ],
            {
                # legacy format
                "group_patterns": ["/var/log/sys*"]
            },
            [
                Result(state=State.OK, notice="Include patterns: /var/log/sys*"),
                Result(
                    state=State.OK, notice="[/var/log/syslog] Age: 3 years 41 days, Size: 384 B"
                ),
                Result(
                    state=State.OK, notice="[/var/log/syslog1] Age: 3 years 41 days, Size: 384 B"
                ),
                Result(state=State.OK, summary="Count: 2"),
                Metric("count", 2),
                Result(state=State.OK, summary="Size: 768 B"),
                Metric("size", 768),
                Result(state=State.OK, summary="Largest size: 384 B"),
                Metric("size_largest", 384),
                Result(state=State.OK, summary="Smallest size: 384 B"),
                Metric("size_smallest", 384),
                Result(state=State.OK, summary="Oldest age: 3 years 41 days"),
                Metric("age_oldest", 98209582),
                Result(state=State.OK, summary="Newest age: 3 years 41 days"),
                Metric("age_newest", 98209582),
            ],
        ),
        (
            [
                ["1563288717"],
                ["/var/log/syslog", "384", "1465079135"],
                ["/var/log/syslog1", "384", "1465079135"],
            ],
            {},
            [
                Result(state=State.UNKNOWN, summary="No group pattern found."),
            ],
        ),
        (
            [
                ["1563288717"],
            ],
            {},
            [
                Result(state=State.UNKNOWN, summary="No group pattern found."),
            ],
        ),
        (
            [
                ["1563288717"],
                ["/var/log/syslog", "384", "1465079135"],
                ["/var/log/syslog1", "384", "1465079135"],
            ],
            {
                # current format
                "group_patterns": [("/var/log/sys*", "/var/log/syslog1")]
            },
            [
                Result(state=State.OK, notice="Include patterns: /var/log/sys*"),
                Result(state=State.OK, notice="Exclude patterns: /var/log/syslog1"),
                Result(
                    state=State.OK, notice="[/var/log/syslog] Age: 3 years 41 days, Size: 384 B"
                ),
                Result(state=State.OK, summary="Count: 1"),
                Metric("count", 1),
                Result(state=State.OK, summary="Size: 384 B"),
                Metric("size", 384),
                Result(state=State.OK, summary="Largest size: 384 B"),
                Metric("size_largest", 384),
                Result(state=State.OK, summary="Smallest size: 384 B"),
                Metric("size_smallest", 384),
                Result(state=State.OK, summary="Oldest age: 3 years 41 days"),
                Metric("age_oldest", 98209582),
                Result(state=State.OK, summary="Newest age: 3 years 41 days"),
                Metric("age_newest", 98209582),
            ],
        ),
    ],
)
def test_check_fileinfo_group_patterns(
    info: StringTable,
    group_pattern: Mapping[str, object],
    expected_result: CheckResult,
) -> None:
    assert expected_result == list(
        fileinfo_plugin.check_fileinfo_groups(
            "banana",
            group_pattern,
            fileinfo_utils.parse_fileinfo(info),
        )
    )


@pytest.mark.parametrize(
    "item, params, expected_result",
    [
        (
            "SMS_checked",
            {
                "group_patterns": [
                    ("/sms/checked/.*", ""),
                ]
            },
            [
                Result(state=State.OK, notice="Include patterns: /sms/checked/.*"),
                Result(state=State.OK, summary="Count: 0"),
                Metric("count", 0),
                Result(state=State.OK, summary="Size: 0 B"),
                Metric("size", 0),
            ],
        ),
        (
            "random_item",
            {
                "group_patterns": [],
            },
            [Result(state=State.UNKNOWN, summary="No group pattern found.")],
        ),
    ],
)
def test_check_fileinfo_group_patterns_get_host_values(
    item: str,
    params: Mapping[str, object],
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            fileinfo_plugin.check_fileinfo_groups(
                item,
                params,
                Fileinfo(
                    reftime=1619516613,
                    files={
                        "/sms/checked/bla": FileinfoItem(
                            name="/sms/checked/bla",
                            missing=False,
                            failed=False,
                            size=0,
                            time=1619515730,
                        )
                    },
                ),
            )
        )
        == expected_result
    )


@pytest.mark.parametrize(
    "info, params, expected_result",
    [
        (
            [
                ["1536557964"],
                ["regular.txt", "4242", "1536421281"],
                ["missing_file.txt", "missing"],
                ["not_readable.txt", "not readable", "1536421281"],
                ["stat_failes.txt", "", "", "0000"],
            ],
            [{}],
            [
                Service(item="regular.txt"),
                Service(item="not_readable.txt"),
                Service(item="stat_failes.txt"),
            ],
        ),
        (
            INFO,
            [
                {
                    "group_patterns": [
                        ("log", ("*syslog*", "")),
                        ("today", ("/tmp/$DATE:%Y%m%d$.txt", "")),
                    ]
                }
            ],
            [
                Service(item="/var/log/aptitude"),
                Service(item="/var/log/aptitude.2.gz"),
            ],
        ),
        (
            [
                ["1536557964"],
                ["[[[header]]]"],
                ["name", "status", "size", "time"],
                ["[[[content]]]"],
            ],
            [{}],
            [],
        ),
        (
            [
                ["1536557964"],
                ["[[[header]]]"],
                ["name", "status", "size", "time"],
                ["[[[content]]]"],
                ["regular.txt", "ok", "4242", "1536421281"],
                ["missing_file.txt", "missing"],
                ["not_readable.txt", "ok", "2323", "1536421281"],
                ["stat_failes.txt", "stat failed: Permission denied"],
            ],
            [{}],
            [
                Service(item="regular.txt"),
                Service(item="not_readable.txt"),
                Service(item="stat_failes.txt"),
            ],
        ),
        (
            [["1536557964"]],
            [{}],
            [],
        ),
        (
            [
                ["1611065402"],
                ["[[[header]]]"],
                ["name", "status", "size", "time"],
                ["[[[content]]]"],
                ["/root/anaconda-ks.cfg", "ok", "6006", "1582708355"],
                ["1611065406"],
                [
                    "/SAP HANA PHT 00/daemon_wwfcsunil286s.dc.ege.ds.30000.336.trc",
                    "11072435",
                    "1609376403",
                ],
                ["/SAP HANA PHT 00/backup.log.3.gz", "425", "1609773942"],
                [
                    "/SAP HANA PHT 00/daemon_wwfcsunil286s_065255__children.trc",
                    "1923",
                    "1607339609",
                ],
                ["/SAP HANA PHT 00/stderr2", "793", "1611064087"],
            ],
            [{}],
            [
                Service(item="/root/anaconda-ks.cfg"),
                Service(item="/SAP HANA PHT 00/daemon_wwfcsunil286s.dc.ege.ds.30000.336.trc"),
                Service(item="/SAP HANA PHT 00/backup.log.3.gz"),
                Service(item="/SAP HANA PHT 00/daemon_wwfcsunil286s_065255__children.trc"),
                Service(item="/SAP HANA PHT 00/stderr2"),
            ],
        ),
    ],
)
def test_fileinfo_discovery(
    info: StringTable,
    params: DiscoveryParams,
    expected_result: DiscoveryResult,
) -> None:
    section = fileinfo_utils.parse_fileinfo(info)
    with time_machine.travel(datetime.datetime(2024, 1, 1, tzinfo=ZoneInfo("UTC"))):
        assert list(fileinfo_utils.discovery_fileinfo(params, section)) == expected_result


@pytest.mark.parametrize(
    "info, item, params, expected_result",
    [
        pytest.param(
            [
                ["1536557964"],
                ["regular.txt", "4242", "1536421281"],
                ["missing_file.txt", "missing"],
                ["not_readable.txt", "not readable", "1536421281"],
                ["stat_failes.txt", "", "", "0000"],
            ],
            "regular.txt",
            {},
            [
                Result(state=State.OK, summary="Size: 4.14 KiB"),
                Metric("size", 4242),
                Result(state=State.OK, summary="Age: 1 day 13 hours"),
                Metric("age", 136683),
            ],
            id="file found",
        ),
        pytest.param(
            [
                ["1536557964"],
                ["regular.txt", "4242", "1536421281"],
                ["missing_file.txt", "missing"],
                ["not_readable.txt", "not readable", "1536421281"],
                ["stat_failes.txt", "", "", "0000"],
            ],
            "missinf_file.txt",
            {},
            [Result(state=State.UNKNOWN, summary="File not found")],
            id="file not found",
        ),
        pytest.param(
            [
                ["1536557964"],
                ["regular.txt", "4242", "1536421281"],
                ["missing_file.txt", "missing"],
                ["not_readable.txt", "not readable", "1536421281"],
                ["stat_failes.txt", "", "", "0000"],
            ],
            "not_readable.txt",
            {},
            [Result(state=State.WARN, summary="File stat failed")],
            id="incorrect size",
        ),
        pytest.param(
            [
                ["1536557964"],
                ["regular.txt", "4242", "1536421281"],
                ["missing_file.txt", "missing"],
                ["not_readable.txt", "not readable", "1536421281"],
                ["stat_failes.txt", "", "", "0000"],
            ],
            "stat_failes.txt",
            {},
            [Result(state=State.WARN, summary="File stat failed")],
            id="missing size and timestamp",
        ),
        pytest.param(
            INFO,
            "/var/log/aptitude",
            {},
            [
                Result(state=State.OK, summary="Size: 0 B"),
                Metric("size", 0),
                Result(state=State.OK, summary="Age: 225 days 6 hours"),
                Metric("age", 19462602),
            ],
            id="empty file",
        ),
        pytest.param(
            INFO,
            "/var/log/aptitude.2.gz",
            {
                "minsize": (5120, 10),
                "maxsize": (5242880, 9663676416),
                "minage": (60, 30),
                "maxage": (3600, 10800),
            },
            [
                Result(state=State.WARN, summary="Size: 3.16 KiB (warn/crit below 5.00 KiB/10 B)"),
                Metric("size", 3234, levels=(5242880.0, 9663676416.0)),
                Result(
                    state=State.CRIT,
                    summary="Age: 280 days 2 hours (warn/crit at 1 hour 0 minutes/3 hours 0 minutes)",
                ),
                Metric("age", 24201996, levels=(3600.0, 10800.0)),
            ],
            id="params with thresholds",
        ),
        pytest.param(
            [
                ["1536557964"],
                ["[[[header]]]"],
                ["name", "status", "size", "time"],
                ["[[[content]]]"],
                ["regular.txt", "ok", "4242", "1536421281"],
                ["missing_file.txt", "missing"],
                ["not_readable.txt", "ok", "2323", "1536421281"],
                ["stat_failes.txt", "stat failed: Permission denied"],
            ],
            "regular.txt",
            {},
            [
                Result(state=State.OK, summary="Size: 4.14 KiB"),
                Metric("size", 4242),
                Result(state=State.OK, summary="Age: 1 day 13 hours"),
                Metric("age", 136683),
            ],
            id="old section format, file found",
        ),
        pytest.param(
            [
                ["1536557964"],
                ["[[[header]]]"],
                ["name", "status", "size", "time"],
                ["[[[content]]]"],
                ["regular.txt", "ok", "4242", "1536421281"],
                ["missing_file.txt", "missing"],
                ["not_readable.txt", "ok", "2323", "1536421281"],
                ["stat_failes.txt", "stat failed: Permission denied"],
            ],
            "missing_file.txt",
            {},
            [
                Result(
                    state=State.UNKNOWN,
                    summary="File not found",
                ),
            ],
            id="old section format, file missing",
        ),
        pytest.param(
            [
                ["1536557964"],
                ["[[[header]]]"],
                ["name", "status", "size", "time"],
                ["[[[content]]]"],
                ["regular.txt", "ok", "4242", "1536421281"],
                ["missing_file.txt", "missing"],
                ["not_readable.txt", "ok", "2323", "1536421281"],
                ["stat_failes.txt", "stat failed: Permission denied"],
            ],
            "stat_failes.txt",
            {},
            [Result(state=State.WARN, summary="File stat failed")],
            id="old section format, file state failed",
        ),
        pytest.param(
            [
                ["1611065402"],
                ["[[[header]]]"],
                ["name", "status", "size", "time"],
                ["[[[content]]]"],
                ["/root/anaconda-ks.cfg", "ok", "6006", "1582708355"],
                ["1611065406"],
                [
                    "/SAP HANA PHT 00/daemon_wwfcsunil286s.dc.ege.ds.30000.336.trc",
                    "11072435",
                    "1609376403",
                ],
                ["/SAP HANA PHT 00/backup.log.3.gz", "425", "1609773942"],
                [
                    "/SAP HANA PHT 00/daemon_wwfcsunil286s_065255__children.trc",
                    "1923",
                    "1607339609",
                ],
                ["/SAP HANA PHT 00/stderr2", "793", "1611064087"],
            ],
            "/SAP HANA PHT 00/backup.log.3.gz",
            {},
            [
                Result(state=State.OK, summary="Size: 425 B"),
                Metric("size", 425),
                Result(state=State.OK, summary="Age: 14 days 22 hours"),
                Metric("age", 1291460),
            ],
            id="2 reftimes, file with the second reftime found",
        ),
        pytest.param(
            [
                ["1611065402"],
                ["[[[header]]]"],
                ["name", "status", "size", "time"],
                ["[[[content]]]"],
                ["/root/anaconda-ks.cfg", "ok", "6006", "1582708355"],
                ["1611065406"],
                [
                    "/SAP HANA PHT 00/daemon_wwfcsunil286s.dc.ege.ds.30000.336.trc",
                    "11072435",
                    "1609376403",
                ],
                ["/SAP HANA PHT 00/backup.log.3.gz", "425", "1609773942"],
                [
                    "/SAP HANA PHT 00/daemon_wwfcsunil286s_065255__children.trc",
                    "1923",
                    "1607339609",
                ],
                ["/SAP HANA PHT 00/stderr2", "793", "1611064087"],
            ],
            "/root/anaconda-ks.cfg",
            {},
            [
                Result(state=State.OK, summary="Size: 5.87 KiB"),
                Metric("size", 6006),
                Result(state=State.OK, summary="Age: 328 days 4 hours"),
                Metric("age", 28357047),
            ],
            id="2 reftimes, file with the first reftime found",
        ),
        pytest.param(
            [],
            "fil1234",
            {},
            [Result(state=State.UNKNOWN, summary="Missing reference timestamp")],
            id="empty section",
        ),
    ],
)
def test_fileinfo_check(
    info: StringTable,
    item: str,
    params: Mapping[str, object],
    expected_result: CheckResult,
) -> None:
    section = fileinfo_utils.parse_fileinfo(info)

    check_result = fileinfo_plugin.check_fileinfo(item, params, section)
    assert list(check_result) == expected_result


@pytest.mark.parametrize(
    "info, params, expected_result",
    [
        (
            INFO,
            [
                {
                    "group_patterns": [
                        ("log", ("*syslog*", "")),
                        ("today", ("/tmp/$DATE:%Y%m%d$.txt", "")),
                    ]
                }
            ],
            [
                Service(item="log", parameters={"group_patterns": [("*syslog*", "")]}),
                Service(item="log", parameters={"group_patterns": [("*syslog*", "")]}),
                Service(
                    item="today", parameters={"group_patterns": [("/tmp/$DATE:%Y%m%d$.txt", "")]}
                ),
            ],
        ),
        (
            INFO,
            [
                {
                    "group_patterns": [
                        ("log", ("*syslog*", "")),
                    ]
                },
                {
                    "group_patterns": [
                        ("today", ("/tmp/$DATE:%Y%m%d$.txt", "")),
                    ]
                },
            ],
            [
                Service(item="log", parameters={"group_patterns": [("*syslog*", "")]}),
                Service(item="log", parameters={"group_patterns": [("*syslog*", "")]}),
                Service(
                    item="today", parameters={"group_patterns": [("/tmp/$DATE:%Y%m%d$.txt", "")]}
                ),
            ],
        ),
    ],
)
def test_fileinfo_group_discovery(
    info: StringTable,
    params: DiscoveryParams,
    expected_result: DiscoveryResult,
) -> None:
    section = fileinfo_utils.parse_fileinfo(info)
    with time_machine.travel(datetime.datetime(2024, 1, 1, tzinfo=ZoneInfo("UTC"))):
        assert list(fileinfo_utils.discovery_fileinfo_groups(params, section)) == expected_result


@pytest.mark.parametrize(
    "info, item, params, expected_result",
    [
        pytest.param(
            INFO,
            "log",
            {
                "group_patterns": [("*syslog*", "")],
                "maxsize": (2, 2097152),
                "minage_newest": (5, 2),
                "maxage_oldest": (3600, 3600 * 5),
            },
            [
                Result(state=State.OK, notice="Include patterns: *syslog*"),
                Result(state=State.OK, notice="[/var/log/syslog] Age: 4 seconds, Size: 1.25 MiB"),
                Result(
                    state=State.OK,
                    notice="[/var/log/syslog.1] Age: 7 hours 59 minutes, Size: 1.18 MiB",
                ),
                Result(state=State.OK, summary="Count: 2"),
                Metric("count", 2),
                Result(state=State.CRIT, summary="Size: 2.42 MiB (warn/crit at 2 B/2.00 MiB)"),
                Metric("size", 2542789, levels=(2.0, 2097152.0)),
                Result(state=State.OK, summary="Largest size: 1.25 MiB"),
                Metric("size_largest", 1307632),
                Result(state=State.OK, summary="Smallest size: 1.18 MiB"),
                Metric("size_smallest", 1235157),
                Result(
                    state=State.CRIT,
                    summary="Oldest age: 7 hours 59 minutes (warn/crit at 1 hour 0 minutes/5 hours 0 minutes)",
                ),
                Metric("age_oldest", 28741, levels=(3600.0, 18000.0)),
                Result(
                    state=State.WARN,
                    summary="Newest age: 4 seconds (warn/crit below 5 seconds/2 seconds)",
                ),
                Metric("age_newest", 4),
            ],
            id="regex pattern",
        ),
        pytest.param(
            INFO,
            "today",
            {"group_patterns": [("/tmp/$DATE:%Y%m%d$.txt", "")]},
            [
                Result(state=State.OK, notice="Include patterns: /tmp/$DATE:%Y%m%d$.txt"),
                Result(
                    state=State.OK,
                    notice="[/tmp/20190716.txt] Age: 7 hours 59 minutes, Size: 1.18 MiB",
                ),
                Result(state=State.OK, summary="Date pattern: /tmp/20190716.txt"),
                Result(state=State.OK, summary="Count: 1"),
                Metric("count", 1),
                Result(state=State.OK, summary="Size: 1.18 MiB"),
                Metric("size", 1235157),
                Result(state=State.OK, summary="Largest size: 1.18 MiB"),
                Metric("size_largest", 1235157),
                Result(state=State.OK, summary="Smallest size: 1.18 MiB"),
                Metric("size_smallest", 1235157),
                Result(state=State.OK, summary="Oldest age: 7 hours 59 minutes"),
                Metric("age_oldest", 28741),
                Result(state=State.OK, summary="Newest age: 7 hours 59 minutes"),
                Metric("age_newest", 28741),
            ],
            id="pattern with today's date",
        ),
        pytest.param(
            INFO,
            "log",
            {
                "group_patterns": [("*syslog*", "")],
                "maxsize": (2, 2097152),
                "minage_newest": (5, 2),
                "maxage_oldest": (3600, 3600 * 5),
                "shorten_multiline_output": True,
            },
            [
                Result(state=State.OK, notice="Include patterns: *syslog*"),
                Result(state=State.OK, summary="Count: 2"),
                Metric("count", 2),
                Result(state=State.CRIT, summary="Size: 2.42 MiB (warn/crit at 2 B/2.00 MiB)"),
                Metric("size", 2542789, levels=(2.0, 2097152.0)),
                Result(state=State.OK, summary="Largest size: 1.25 MiB"),
                Metric("size_largest", 1307632),
                Result(state=State.OK, summary="Smallest size: 1.18 MiB"),
                Metric("size_smallest", 1235157),
                Result(
                    state=State.CRIT,
                    summary="Oldest age: 7 hours 59 minutes (warn/crit at 1 hour 0 minutes/5 hours 0 minutes)",
                ),
                Metric("age_oldest", 28741, levels=(3600.0, 18000.0)),
                Result(
                    state=State.WARN,
                    summary="Newest age: 4 seconds (warn/crit below 5 seconds/2 seconds)",
                ),
                Metric("age_newest", 4),
            ],
            id="shorten multiline output",
        ),
        pytest.param(
            INFO_MISSING_TIME_SYSLOG,
            "log",
            {"group_patterns": [("*syslog*", "")], "timeofday": [((8, 0), (9, 0))]},
            [
                Result(state=State.OK, notice="Include patterns: *syslog*"),
                Result(
                    state=State.OK,
                    notice="[/var/log/syslog.1] Age: 7 hours 59 minutes, Size: 1.18 MiB",
                ),
                Result(state=State.OK, summary="Count: 1"),
                Metric("count", 1),
                Result(state=State.OK, summary="Size: 1.18 MiB"),
                Metric("size", 1235157),
                Result(state=State.OK, summary="Largest size: 1.18 MiB"),
                Metric("size_largest", 1235157),
                Result(state=State.OK, summary="Smallest size: 1.18 MiB"),
                Metric("size_smallest", 1235157),
                Result(state=State.OK, summary="Oldest age: 7 hours 59 minutes"),
                Metric("age_oldest", 28741),
                Result(state=State.OK, summary="Newest age: 7 hours 59 minutes"),
                Metric("age_newest", 28741),
            ],
            id="missing time",
        ),
    ],
)
@time_machine.travel(datetime.datetime(2021, 7, 12, 12, tzinfo=ZoneInfo("UTC")))
def test_fileinfo_groups_check(
    info: StringTable,
    item: str,
    params: Mapping[str, object],
    expected_result: CheckResult,
) -> None:
    section = fileinfo_utils.parse_fileinfo(info)
    assert list(fileinfo_plugin.check_fileinfo_groups(item, params, section)) == expected_result
