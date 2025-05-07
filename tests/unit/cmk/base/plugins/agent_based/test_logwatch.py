#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pathlib
from collections.abc import Iterable

import pytest
from pytest_mock import MockerFixture

from cmk.base.plugins.agent_based import logwatch
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.utils import logwatch as logwatch_


@pytest.mark.parametrize(
    "group_patterns, filename, expected",
    [
        ([], "lumberjacks.log", {}),
        (
            [("plain_group", ("*jack*", ""))],
            "lumberjacks.log",
            {
                "plain_group": {("*jack*", "")},
            },
        ),
        ([("plain_group", ("*jack*", "*.log"))], "lumberjacks.log", {}),
        (
            [("plain_group", ("~.*\\..*", ""))],
            "lumberjacks.log",
            {"plain_group": {("~.*\\..*", "")}},
        ),
        (
            [("%s_group", ("~.{6}(.ack)", ""))],
            "lumberjacks.log",
            {
                "jack_group": {("~.{6}jack", "")},
            },
        ),
        (
            [("%s", ("~(.).*", "")), ("%s", ("~lumberjacks.([l])og", ""))],
            "lumberjacks.log",
            {
                "l": {("~l.*", ""), ("~lumberjacks.log", "")},
            },
        ),
        (
            [("%s%s", ("~lum(ber).{8}(.)", "~ladida"))],
            "lumberjacks.log",
            {
                "berg": {("~lumber.{8}g", "~ladida")},
            },
        ),
    ],
)
def test_logwatch_groups_of_logfile(
    group_patterns: list[tuple[str, logwatch.GroupingPattern]],
    filename: str,
    expected: dict[str, set[logwatch.GroupingPattern]],
) -> None:
    actual = logwatch._groups_of_logfile(group_patterns, filename)
    assert actual == expected


@pytest.mark.parametrize(
    "group_patterns, filename",
    [
        ([("%s_group", ("~.{6}.ack", ""))], "lumberjacks.log"),
    ],
)
def test_logwatch_groups_of_logfile_exception(
    group_patterns: list[tuple[str, logwatch.GroupingPattern]], filename: str
) -> None:
    with pytest.raises(RuntimeError):
        logwatch._groups_of_logfile(group_patterns, filename)


SECTION1 = logwatch_.Section(
    errors=[],
    logfiles={
        "mylog": {
            "attr": "ok",
            "lines": {"test-batch-id": ["C whoha! Someone mooped!"]},
        },
        "missinglog": {
            "attr": "missing",
            "lines": {},
        },
        "unreadablelog": {
            "attr": "cannotopen",
            "lines": {},
        },
        "empty.log": {
            "attr": "ok",
            "lines": {},
        },
        "my_other_log": {
            "attr": "ok",
            "lines": {"test-batch-id": ["W watch your step!"]},
        },
    },
)


def test_discovery_single(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(logwatch_, "get_ec_rule_params", lambda: [])
    assert sorted(
        logwatch.discover_logwatch_single([], SECTION1),
        key=lambda s: s.item or "",
    ) == [
        Service(item="empty.log"),
        Service(item="my_other_log"),
        Service(item="mylog"),
        Service(item="unreadablelog"),
    ]

    assert not list(logwatch.discover_logwatch_groups([], SECTION1))


@pytest.mark.parametrize(
    "log_name, expected_result",
    [
        pytest.param(
            "empty.log",
            [
                Result(
                    state=State.OK,
                    summary="No error messages",
                ),
            ],
        ),
        pytest.param(
            "my_other_log",
            [
                Result(
                    state=State.WARN,
                    summary='1 WARN messages (Last worst: "watch your step!")',
                ),
            ],
        ),
        pytest.param(
            "mylog",
            [
                Result(
                    state=State.CRIT,
                    summary='1 CRIT messages (Last worst: "whoha! Someone mooped!")',
                ),
            ],
        ),
        pytest.param(
            "unreadablelog",
            [
                Result(state=State.CRIT, summary="Could not read log file 'unreadablelog'"),
                Result(state=State.OK, summary="No error messages"),
            ],
        ),
    ],
)
def test_check_single(
    monkeypatch: pytest.MonkeyPatch, log_name: str, expected_result: Iterable[Result]
) -> None:
    monkeypatch.setattr(logwatch, "get_value_store", lambda: {})
    monkeypatch.setattr(logwatch, "_compile_params", lambda _item: [])
    monkeypatch.setattr(logwatch, "host_name", lambda: "test-host")

    assert list(logwatch.check_logwatch_node(log_name, SECTION1)) == expected_result


@pytest.mark.parametrize(
    "group_name, reg_pattern, expected_result",
    [
        pytest.param(
            "no_errors",
            [("whatever", "")],
            [
                Result(
                    state=State.OK,
                    summary="No error messages",
                ),
            ],
        ),
        pytest.param(
            "matching_pattern",
            [("~log\\d$", "")],
            [
                Result(
                    state=State.WARN,
                    summary='2 WARN messages (Last worst: "very warning")',
                ),
            ],
        ),
        pytest.param(
            "other_matching_pattern",
            [("~log_.*", "")],
            [
                Result(
                    state=State.WARN,
                    summary='1 WARN messages (Last worst: "another warning")',
                ),
            ],
        ),
    ],
)
def test_check_logwatch_groups_node(
    monkeypatch: pytest.MonkeyPatch,
    group_name: str,
    reg_pattern: Iterable[tuple[str, str]],
    expected_result: Iterable[Result],
) -> None:
    monkeypatch.setattr(logwatch, "get_value_store", lambda: {})
    monkeypatch.setattr(logwatch, "_compile_params", lambda _item: [])
    monkeypatch.setattr(logwatch, "host_name", lambda: "test-host")

    section = logwatch_.Section(
        errors=[],
        logfiles={
            "log1": {
                "attr": "ok",
                "lines": {"batch1": ["W be cautious!"]},
            },
            "log2": {
                "attr": "ok",
                "lines": {"batch": ["W very warning"]},
            },
            "log_a": {
                "attr": "ok",
                "lines": {"batch2": ["W another warning"]},
            },
        },
    )

    assert (
        list(
            logwatch.check_logwatch_groups_node(
                group_name,
                {"group_patterns": reg_pattern},
                section,
            )
        )
        == expected_result
    )


SECTION2 = logwatch_.Section(
    errors=[],
    logfiles={
        "log1": {
            "attr": "ok",
            "lines": {},
        },
        "log2": {
            "attr": "ok",
            "lines": {},
        },
        "log3": {
            "attr": "missing",
            "lines": {},
        },
        "log4": {
            "attr": "cannotopen",
            "lines": {},
        },
        "log5": {
            "attr": "ok",
            "lines": {},
        },
    },
)


def test_logwatch_discover_single_restrict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        logwatch_,
        "get_ec_rule_params",
        lambda: [{"restrict_logfiles": [".*2"]}],
    )
    assert sorted(
        logwatch.discover_logwatch_single([], SECTION2),
        key=lambda s: s.item or "",
    ) == [
        Service(item="log1"),
        Service(item="log4"),
        Service(item="log5"),
    ]


def test_logwatch_discover_single_groups(monkeypatch: pytest.MonkeyPatch) -> None:
    params = [
        {
            "grouping_patterns": [
                ("my_group", ("~log.*", "~.*1")),
            ]
        }
    ]

    monkeypatch.setattr(logwatch_, "get_ec_rule_params", lambda: [])

    assert list(logwatch.discover_logwatch_single(params, SECTION2)) == [
        Service(item="log1"),
    ]


def test_logwatch_discover_groups(monkeypatch: pytest.MonkeyPatch) -> None:
    params = [
        {
            "grouping_patterns": [
                ("my_%s_group", ("~(log)[^5]", "~.*1")),
                ("my_%s_group", ("~(log).*", "~.*5")),
            ],
        }
    ]

    monkeypatch.setattr(logwatch_, "get_ec_rule_params", lambda: [])

    assert list(logwatch.discover_logwatch_groups(params, SECTION2)) == [
        Service(
            item="my_log_group",
            parameters={
                "group_patterns": [
                    ("~log.*", "~.*5"),
                    ("~log[^5]", "~.*1"),
                ],
            },
        ),
    ]


@pytest.fixture(name="logmsg_file_path")
def fixture_logmsg_file_path(
    mocker: MockerFixture,
    tmp_path: pathlib.Path,
) -> None:
    mocker.patch.object(
        logwatch,
        "_logmsg_file_path",
        lambda item: tmp_path / item.replace("/", "\\"),
    )


@pytest.mark.usefixtures("logmsg_file_path")
def test_check_logwatch_generic_no_messages() -> None:
    item = "/tmp/app.log"
    assert list(
        logwatch.check_logwatch_generic(
            item=item,
            patterns={},
            loglines=[],
            found=True,
            max_filesize=logwatch._LOGWATCH_MAX_FILESIZE,
        )
    ) == [
        Result(state=State.OK, summary="No error messages"),
    ]
    assert not logwatch._logmsg_file_path(item).exists()


@pytest.mark.usefixtures("logmsg_file_path")
def test_check_logwatch_generic_no_reclassify() -> None:
    item = "/tmp/enterprise.log"
    lines = [
        ". klingons are attacking",
        "C red alert",
        ". more context",
    ]

    assert list(
        logwatch.check_logwatch_generic(
            item=item,
            patterns={},
            loglines=lines,
            found=True,
            max_filesize=logwatch._LOGWATCH_MAX_FILESIZE,
        )
    ) == [
        Result(state=State.CRIT, summary='1 CRIT messages (Last worst: "red alert")'),
    ]
    assert logwatch._logmsg_file_path(item).read_text().splitlines()[-len(lines) :] == lines


@pytest.mark.usefixtures("logmsg_file_path")
def test_check_logwatch_generic_with_reclassification() -> None:
    item = "/tmp/enterprise.log"
    lines = [
        ". klingons are attacking",
        "C red alert",
        ". more context",
    ]

    assert list(
        logwatch.check_logwatch_generic(
            item=item,
            patterns={
                "reclassify_patterns": [
                    ("C", ".*klingon.*", "galatic conflict"),
                    ("I", "123", ""),
                ],
            },
            loglines=lines,
            found=True,
            max_filesize=logwatch._LOGWATCH_MAX_FILESIZE,
        )
    ) == [
        Result(state=State.CRIT, summary='2 CRIT messages (Last worst: "red alert")'),
    ]
    assert logwatch._logmsg_file_path(item).read_text().splitlines()[-len(lines) :] == [
        "C klingons are attacking",
        "C red alert",
        ". more context",
    ]


@pytest.mark.usefixtures("logmsg_file_path")
def test_check_logwatch_generic_missing() -> None:
    item = "item"
    assert list(
        logwatch.check_logwatch_generic(
            item=item,
            patterns={},
            loglines=[],
            found=False,
            max_filesize=logwatch._LOGWATCH_MAX_FILESIZE,
        )
    ) == [
        Result(state=State.UNKNOWN, summary="log not present anymore"),
    ]
    assert not logwatch._logmsg_file_path(item).exists()
