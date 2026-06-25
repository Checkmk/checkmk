#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from cmk.agent_based.v2 import CheckPlugin, Result, Service, State
from cmk.logwatch.config import (
    ParameterLogwatchEc,
    ParameterLogwatchRules,
    set_global_state,
    unset_global_state,
)
from cmk.plugins.logwatch.agent_based import commons as logwatch_
from cmk.plugins.logwatch.agent_based import logwatch

TEST_DISCO_PARAMS = [logwatch_.ParameterLogwatchGroups(host_name="test-host", grouping_patterns=[])]


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
    actual = logwatch._groups_of_logfile(group_patterns, filename)  # noqa: SLF001
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
        logwatch._groups_of_logfile(group_patterns, filename)  # noqa: SLF001


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
        "my_other_log": {"attr": "ok", "lines": {"test-batch-id": ["W watch your step!"]}},
    },
)


class _LogwatchConfigDummy:
    def __init__(
        self, ec_all: Sequence[ParameterLogwatchEc] = (), msg_dir: Path = Path("/dev/null")
    ) -> None:
        self._ec_all = ec_all
        self.base_spool_path = Path("/dev/null")
        self.omd_root = Path("/dev/null")
        self.msg_dir = msg_dir
        self.debug = False

    def logwatch_rules_all(
        self, *, host_name: str, plugin: CheckPlugin, logfile: str
    ) -> Sequence[ParameterLogwatchRules]:
        return ()

    def logwatch_ec_all(self, host_name: str) -> Sequence[ParameterLogwatchEc]:
        return self._ec_all


@contextmanager
def _logwatch_state(config: _LogwatchConfigDummy) -> Iterator[None]:
    set_global_state(config)
    try:
        yield
    finally:
        unset_global_state()


def test_discovery_single() -> None:
    with _logwatch_state(_LogwatchConfigDummy()):
        assert sorted(
            logwatch.discover_logwatch_single(TEST_DISCO_PARAMS, SECTION1),
            key=lambda s: s.item or "",
        ) == [
            Service(item="empty.log"),
            Service(item="my_other_log"),
            Service(item="mylog"),
            Service(item="unreadablelog"),
        ]

        assert not list(logwatch.discover_logwatch_groups(TEST_DISCO_PARAMS, SECTION1))


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
    monkeypatch: pytest.MonkeyPatch,
    log_name: str,
    expected_result: Iterable[Result],
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(logwatch, "get_value_store", dict)
    with _logwatch_state(_LogwatchConfigDummy(msg_dir=tmp_path)):
        monkeypatch.setattr(
            logwatch_,
            logwatch_.compile_reclassify_params.__name__,
            lambda _item: logwatch_.ReclassifyParameters((), {}),
        )

        assert (
            list(
                logwatch.check_logwatch_node(
                    log_name, {"host_name": "test-host", "is_preview": False}, SECTION1
                )
            )
            == expected_result
        )


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
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(logwatch, "get_value_store", dict)
    with _logwatch_state(_LogwatchConfigDummy(msg_dir=tmp_path)):
        monkeypatch.setattr(
            logwatch_,
            logwatch_.compile_reclassify_params.__name__,
            lambda _item: logwatch_.ReclassifyParameters((), {}),
        )

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
                    {"group_patterns": reg_pattern, "host_name": "test-host", "is_preview": False},
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


def test_logwatch_discover_single_restrict() -> None:
    with _logwatch_state(
        _LogwatchConfigDummy(
            ec_all=[
                ParameterLogwatchEc(
                    host_name="irrelevant",
                    service_level=10,
                    is_preview=False,
                    restrict_logfiles=[".*2"],
                )
            ]
        )
    ):
        assert sorted(
            logwatch.discover_logwatch_single(TEST_DISCO_PARAMS, SECTION2),
            key=lambda s: s.item or "",
        ) == [
            Service(item="log1"),
            Service(item="log4"),
            Service(item="log5"),
        ]


def test_logwatch_discover_single_groups(monkeypatch: pytest.MonkeyPatch) -> None:
    params = [
        logwatch_.ParameterLogwatchGroups(
            grouping_patterns=[
                ("my_group", ("~log.*", "~.*1")),
            ],
            host_name="test-host",
        )
    ]

    with _logwatch_state(_LogwatchConfigDummy()):
        assert list(logwatch.discover_logwatch_single(params, SECTION2)) == [
            Service(item="log1"),
        ]


def test_logwatch_discover_groups(monkeypatch: pytest.MonkeyPatch) -> None:
    params = [
        logwatch_.ParameterLogwatchGroups(
            grouping_patterns=[
                ("my_%s_group", ("~(log)[^5]", "~.*1")),
                ("my_%s_group", ("~(log).*", "~.*5")),
            ],
            host_name="test-host",
        )
    ]

    with _logwatch_state(_LogwatchConfigDummy()):
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
    tmp_path: Path,
) -> None:
    mocker.patch.object(
        logwatch,
        "_logmsg_file_path",
        lambda _base, item, _host_name: tmp_path / item.replace("/", "\\"),
    )


def test_check_logwatch_generic_no_messages(tmp_path: Path) -> None:
    with _logwatch_state(_LogwatchConfigDummy(msg_dir=tmp_path)):
        item = "/tmp/app.log"
        assert list(
            logwatch.check_logwatch_generic(
                item=item,
                reclassify_parameters=logwatch_.ReclassifyParameters((), {}),
                loglines=[],
                found=True,
                max_filesize=logwatch._LOGWATCH_MAX_FILESIZE,  # noqa: SLF001
                host_name="test-host",
                is_preview=False,
            )
        ) == [
            Result(state=State.OK, summary="No error messages"),
        ]
        assert not logwatch._logmsg_file_path(tmp_path, item, "test-host").exists()  # noqa: SLF001


@pytest.mark.usefixtures("logmsg_file_path")
def test_check_logwatch_generic_no_reclassify(tmp_path: Path) -> None:
    with _logwatch_state(_LogwatchConfigDummy(msg_dir=tmp_path)):
        item = "/tmp/enterprise.log"
        lines = [
            ". klingons are attacking",
            "C red alert",
            ". more context",
        ]

        assert list(
            logwatch.check_logwatch_generic(
                item=item,
                reclassify_parameters=logwatch_.ReclassifyParameters((), {}),
                loglines=lines,
                found=True,
                max_filesize=logwatch._LOGWATCH_MAX_FILESIZE,  # noqa: SLF001
                host_name="test-host",
                is_preview=False,
            )
        ) == [
            Result(state=State.CRIT, summary='1 CRIT messages (Last worst: "red alert")'),
        ]
        assert (
            logwatch._logmsg_file_path(tmp_path, item, "test-host")  # noqa: SLF001
            .read_text()
            .splitlines()[-len(lines) :]
            == lines
        )


@pytest.mark.usefixtures("logmsg_file_path")
def test_check_logwatch_generic_with_reclassification(tmp_path: Path) -> None:
    with _logwatch_state(_LogwatchConfigDummy(msg_dir=tmp_path)):
        item = "/tmp/enterprise.log"
        lines = [
            ". klingons are attacking",
            "C red alert",
            ". more context",
        ]

        assert list(
            logwatch.check_logwatch_generic(
                item=item,
                reclassify_parameters=logwatch_.ReclassifyParameters(
                    patterns=[
                        ("C", ".*klingon.*", "galatic conflict"),
                        ("I", "123", ""),
                    ],
                    states={},
                ),
                loglines=lines,
                found=True,
                max_filesize=logwatch._LOGWATCH_MAX_FILESIZE,  # noqa: SLF001
                host_name="test-host",
                is_preview=False,
            )
        ) == [
            Result(state=State.CRIT, summary='2 CRIT messages (Last worst: "red alert")'),
        ]
        path = logwatch._logmsg_file_path(tmp_path, item, "test-host")  # noqa: SLF001
        assert path.read_text().splitlines()[-len(lines) :] == [
            "C klingons are attacking",
            "C red alert",
            ". more context",
        ]


@pytest.mark.usefixtures("logmsg_file_path")
def test_check_logwatch_generic_missing(tmp_path: Path) -> None:
    with _logwatch_state(_LogwatchConfigDummy(msg_dir=tmp_path)):
        item = "item"
        assert list(
            logwatch.check_logwatch_generic(
                item=item,
                reclassify_parameters=logwatch_.ReclassifyParameters((), {}),
                loglines=[],
                found=False,
                max_filesize=logwatch._LOGWATCH_MAX_FILESIZE,  # noqa: SLF001
                host_name="test-host",
                is_preview=False,
            )
        ) == [
            Result(state=State.UNKNOWN, summary="log not present anymore"),
        ]
        assert not logwatch._logmsg_file_path(tmp_path, item, "test-host").exists()  # noqa: SLF001


@pytest.mark.usefixtures("logmsg_file_path")
def test_check_logwatch_generic_reclassify_to_ok_shows_summary(tmp_path: Path) -> None:
    with _logwatch_state(_LogwatchConfigDummy(msg_dir=tmp_path)):
        # Create reclassify parameters to reclassify Critical to OK
        reclassify_parameters = logwatch_.ReclassifyParameters(
            patterns=[],
            states={"c_to": "O"},
        )

        assert list(
            logwatch.check_logwatch_generic(
                item="item",
                reclassify_parameters=reclassify_parameters,
                loglines=[
                    "C One critical error occurred",
                    "C Second critical error",
                ],
                found=True,
                max_filesize=logwatch._LOGWATCH_MAX_FILESIZE,  # noqa: SLF001
                host_name="test-host",
                is_preview=False,
            )
        ) == [
            Result(state=State.OK, summary='2 OK messages (Last worst: "Second critical error")'),
        ]


@pytest.mark.usefixtures("logmsg_file_path")
def test_check_logwatch_generic_multiline_logline_to_summary_details(tmp_path: Path) -> None:
    with _logwatch_state(_LogwatchConfigDummy(msg_dir=tmp_path)):
        assert list(
            logwatch.check_logwatch_generic(
                item="item",
                reclassify_parameters=logwatch_.ReclassifyParameters((), {}),
                loglines=[
                    "C One critical error occurred",
                    "C Second critical error\nWith a second line\nand a third line",
                ],
                found=True,
                max_filesize=logwatch._LOGWATCH_MAX_FILESIZE,  # noqa: SLF001
                host_name="test-host",
                is_preview=False,
            )
        ) == [
            Result(
                state=State.CRIT,
                summary='2 CRIT messages (Last worst: "Second critical error',
                details='With a second line\nand a third line")',
            ),
        ]


@pytest.mark.usefixtures("logmsg_file_path")
def test_check_logwatch_generic_preview_no_file_written(tmp_path: Path) -> None:
    """In preview mode, results are still produced but no logmsg file is created."""
    with _logwatch_state(_LogwatchConfigDummy(msg_dir=tmp_path)):
        item = "/tmp/app.log"
        result = list(
            logwatch.check_logwatch_generic(
                item=item,
                reclassify_parameters=logwatch_.ReclassifyParameters((), {}),
                loglines=["C critical error"],
                found=True,
                max_filesize=logwatch._LOGWATCH_MAX_FILESIZE,  # noqa: SLF001
                host_name="test-host",
                is_preview=True,
            )
        )
        assert result == [
            Result(state=State.CRIT, summary='1 CRIT messages (Last worst: "critical error")')
        ]
        assert not logwatch._logmsg_file_path(tmp_path, item, "test-host").exists()  # noqa: SLF001


@pytest.mark.usefixtures("logmsg_file_path")
def test_check_logwatch_generic_preview_existing_file_unchanged(tmp_path: Path) -> None:
    """In preview mode, an existing logmsg file is read for history but not modified."""
    with _logwatch_state(_LogwatchConfigDummy(msg_dir=tmp_path)):
        item = "/tmp/app.log"
        # Normal run to populate the cache file.
        list(
            logwatch.check_logwatch_generic(
                item=item,
                reclassify_parameters=logwatch_.ReclassifyParameters((), {}),
                loglines=["C existing error"],
                found=True,
                max_filesize=logwatch._LOGWATCH_MAX_FILESIZE,  # noqa: SLF001
                host_name="test-host",
                is_preview=False,
            )
        )
        file_path = logwatch._logmsg_file_path(tmp_path, item, "test-host")  # noqa: SLF001
        original_content = file_path.read_text()

        # Preview run with new lines — file must remain unchanged.
        result = list(
            logwatch.check_logwatch_generic(
                item=item,
                reclassify_parameters=logwatch_.ReclassifyParameters((), {}),
                loglines=["C new error seen only in preview"],
                found=True,
                max_filesize=logwatch._LOGWATCH_MAX_FILESIZE,  # noqa: SLF001
                host_name="test-host",
                is_preview=True,
            )
        )
        assert result  # results are still yielded
        assert file_path.read_text() == original_content
