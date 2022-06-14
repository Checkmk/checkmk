from copy import deepcopy

import pytest
from freezegun import freeze_time

from cmk.base.plugins.agent_based import fileinfo as fileinfo_plugin
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.utils import fileinfo as fileinfo_utils
from cmk.base.plugins.agent_based.utils.fileinfo import Fileinfo, FileinfoItem

pytestmark = pytest.mark.checks

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
            {"group_patterns": [("banana", ("/banana/*", ""))]},
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
            {"group_patterns": []},
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
            {"group_patterns": [("banana", ("/banana/*", ""))]},
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
def test_check_fileinfo_group_no_files(info, parsed, discovery_params, expected_result) -> None:
    """Test that the check returns an OK status when there are no files."""
    assert fileinfo_utils.parse_fileinfo(info) == parsed
    assert not list(fileinfo_plugin.discovery_fileinfo_groups(discovery_params, parsed))
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
def test_check_fileinfo_group_no_matching_files(info, parsed, expected_result) -> None:
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
def test_check_fileinfo_group_patterns(info, group_pattern, expected_result) -> None:
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
def test_check_fileinfo_group_patterns_host_extra_conf(item, params, expected_result) -> None:
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
def test_fileinfo_discovery(info, params, expected_result) -> None:
    section = fileinfo_utils.parse_fileinfo(info)

    discovery_result = fileinfo_utils.discovery_fileinfo(params, section)
    assert list(discovery_result) == expected_result


@pytest.mark.parametrize(
    "info, item, params, expected_result",
    [
        (
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
                Result(state=State.OK, summary="Size: 4,242 B"),
                Metric("size", 4242),
                Result(state=State.OK, summary="Age: 1 day 13 hours"),
                Metric("age", 136683),
            ],
        ),
        (
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
        ),
        (
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
        ),
        (
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
        ),
        (
            INFO,
            "/var/log/aptitude",
            {},
            [
                Result(state=State.OK, summary="Size: 0 B"),
                Metric("size", 0),
                Result(state=State.OK, summary="Age: 225 days 6 hours"),
                Metric("age", 19462602),
            ],
        ),
        (
            INFO,
            "/var/log/aptitude.2.gz",
            {
                "minsize": (5120, 10),
                "maxsize": (5242880, 9663676416),
                "minage": (60, 30),
                "maxage": (3600, 10800),
            },
            [
                Result(state=State.WARN, summary="Size: 3,234 B (warn/crit below 5,120 B/10 B)"),
                Metric("size", 3234, levels=(5242880.0, 9663676416.0)),
                Result(
                    state=State.CRIT,
                    summary="Age: 280 days 2 hours (warn/crit at 1 hour 0 minutes/3 hours 0 minutes)",
                ),
                Metric("age", 24201996, levels=(3600.0, 10800.0)),
            ],
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
            "regular.txt",
            {},
            [
                Result(state=State.OK, summary="Size: 4,242 B"),
                Metric("size", 4242),
                Result(state=State.OK, summary="Age: 1 day 13 hours"),
                Metric("age", 136683),
            ],
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
            "missinf_file.txt",
            {},
            [
                Result(
                    state=State.UNKNOWN,
                    summary="File not found",
                ),
            ],
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
            "stat_failes.txt",
            {},
            [Result(state=State.WARN, summary="File stat failed")],
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
            "/SAP HANA PHT 00/backup.log.3.gz",
            {},
            [
                Result(state=State.OK, summary="Size: 425 B"),
                Metric("size", 425),
                Result(state=State.OK, summary="Age: 14 days 22 hours"),
                Metric("age", 1291460),
            ],
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
            "/root/anaconda-ks.cfg",
            {},
            [
                Result(state=State.OK, summary="Size: 6,006 B"),
                Metric("size", 6006),
                Result(state=State.OK, summary="Age: 328 days 4 hours"),
                Metric("age", 28357047),
            ],
        ),
        ([], "fil1234", {}, [Result(state=State.UNKNOWN, summary="Missing reference timestamp")]),
    ],
)
def test_fileinfo_check(info, item, params, expected_result) -> None:
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
def test_fileinfo_group_discovery(info, params, expected_result) -> None:
    section = fileinfo_utils.parse_fileinfo(info)

    discovery_result = fileinfo_utils.discovery_fileinfo_groups(params, section)
    assert list(discovery_result) == expected_result


@pytest.mark.parametrize(
    "info, item, params, expected_result",
    [
        (
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
                Result(
                    state=State.OK, notice="[/var/log/syslog] Age: 4 seconds, Size: 1,307,632 B"
                ),
                Result(
                    state=State.OK,
                    notice="[/var/log/syslog.1] Age: 7 hours 59 minutes, Size: 1,235,157 B",
                ),
                Result(state=State.OK, summary="Count: 2"),
                Metric("count", 2),
                Result(
                    state=State.CRIT, summary="Size: 2,542,789 B (warn/crit at 2 B/2,097,152 B)"
                ),
                Metric("size", 2542789, levels=(2.0, 2097152.0)),
                Result(state=State.OK, summary="Largest size: 1,307,632 B"),
                Metric("size_largest", 1307632),
                Result(state=State.OK, summary="Smallest size: 1,235,157 B"),
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
        ),
        (
            INFO,
            "today",
            {"group_patterns": [("/tmp/$DATE:%Y%m%d$.txt", "")]},
            [
                Result(state=State.OK, notice="Include patterns: /tmp/$DATE:%Y%m%d$.txt"),
                Result(
                    state=State.OK,
                    notice="[/tmp/20190716.txt] Age: 7 hours 59 minutes, Size: 1,235,157 B",
                ),
                Result(state=State.OK, summary="Date pattern: /tmp/20190716.txt"),
                Result(state=State.OK, summary="Count: 1"),
                Metric("count", 1),
                Result(state=State.OK, summary="Size: 1,235,157 B"),
                Metric("size", 1235157),
                Result(state=State.OK, summary="Largest size: 1,235,157 B"),
                Metric("size_largest", 1235157),
                Result(state=State.OK, summary="Smallest size: 1,235,157 B"),
                Metric("size_smallest", 1235157),
                Result(state=State.OK, summary="Oldest age: 7 hours 59 minutes"),
                Metric("age_oldest", 28741),
                Result(state=State.OK, summary="Newest age: 7 hours 59 minutes"),
                Metric("age_newest", 28741),
            ],
        ),
        (
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
                Result(
                    state=State.CRIT, summary="Size: 2,542,789 B (warn/crit at 2 B/2,097,152 B)"
                ),
                Metric("size", 2542789, levels=(2.0, 2097152.0)),
                Result(state=State.OK, summary="Largest size: 1,307,632 B"),
                Metric("size_largest", 1307632),
                Result(state=State.OK, summary="Smallest size: 1,235,157 B"),
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
        ),
        (
            INFO_MISSING_TIME_SYSLOG,
            "log",
            {"group_patterns": [("*syslog*", "")], "timeofday": [((8, 0), (9, 0))]},
            [
                Result(state=State.OK, notice="Include patterns: *syslog*"),
                Result(
                    state=State.OK,
                    notice="[/var/log/syslog.1] Age: 7 hours 59 minutes, Size: 1,235,157 B",
                ),
                Result(state=State.OK, summary="Count: 1"),
                Metric("count", 1),
                Result(state=State.OK, summary="Size: 1,235,157 B"),
                Metric("size", 1235157),
                Result(state=State.OK, summary="Largest size: 1,235,157 B"),
                Metric("size_largest", 1235157),
                Result(state=State.OK, summary="Smallest size: 1,235,157 B"),
                Metric("size_smallest", 1235157),
                Result(state=State.OK, summary="Oldest age: 7 hours 59 minutes"),
                Metric("age_oldest", 28741),
                Result(state=State.OK, summary="Newest age: 7 hours 59 minutes"),
                Metric("age_newest", 28741),
                Result(state=State.OK, summary="Out of relevant time of day"),
            ],
        ),
    ],
)
@freeze_time("2021-07-12 12:00")
def test_fileinfo_groups_check(info, item, params, expected_result) -> None:
    section = fileinfo_utils.parse_fileinfo(info)

    check_result = fileinfo_plugin.check_fileinfo_groups(item, params, section)
    assert list(check_result) == expected_result
