#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import logging
import os
from collections.abc import Iterator, Sequence

import pytest

from cmk.plugins.sql.active_check import check_sql

_REQUIRED_ARGS = ["check_sql", "-n", "db", "-u", "monitoring", "--password", "secret"]


@pytest.fixture(name="restore_root_logging")
def _restore_root_logging() -> Iterator[None]:
    # parse_args configures the root logger with a handler bound to this test's stderr
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    yield
    root.handlers[:] = handlers
    root.setLevel(level)


class _FakeCursor:
    def __init__(self, rows: list[tuple[object, ...]], fail: bool = False) -> None:
        self.rows = rows
        self.fail = fail
        self.executed: list[str] = []
        self.procedure_calls: list[tuple[str, list[str]]] = []
        self.closed = False

    def execute(self, cmd: str) -> None:
        if self.fail:
            raise RuntimeError("syntax error")
        self.executed.append(cmd)

    def callproc(self, name: str, params: Sequence[str]) -> None:
        self.procedure_calls.append((name, list(params)))

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.rows

    def close(self) -> None:
        self.closed = True


class _FakeConnection:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor
        self.closed = False

    def cursor(self) -> _FakeCursor:
        return self._cursor

    def close(self) -> None:
        self.closed = True


@pytest.mark.parametrize(
    "result, warn, crit, reference",
    [
        ([[3, "count"]], (3, 5), (float("-inf"), 5), (0, "count: 3.0")),
        ([[2, "count"]], (3, 5), (float("-inf"), 5), (1, "count: 2.0")),
        ([[5, "count"]], (3, 5), (float("-inf"), 5), (2, "count: 5.0")),
        ([[5, "count"]], (3, 5), (float("-inf"), 8), (1, "count: 5.0")),
    ],
)
def test_process_result(  # type: ignore[misc]
    result: list,
    warn: tuple[int, int],
    crit: tuple[float, int],
    reference: tuple[int, str],
) -> None:
    assert (
        check_sql.process_result(
            result=result,
            warn=warn,
            crit=crit,
            metrics=None,
            debug=False,
        )
        == reference
    )


@pytest.mark.parametrize("dbms", ["postgres", "mysql", "mssql", "db2", "sqlanywhere"])
def test_statement_is_executed_and_rows_returned(dbms: str) -> None:
    cursor = _FakeCursor([(0, "all fine")])

    result = check_sql.execute(dbms, _FakeConnection(cursor), "SELECT 0, 'all fine'", [])

    assert (result, cursor.executed) == ([(0, "all fine")], ["SELECT 0, 'all fine'"])


@pytest.mark.parametrize("dbms", ["postgres", "mysql", "db2", "sqlanywhere"])
def test_procedure_is_called_with_input_values(dbms: str) -> None:
    cursor = _FakeCursor([(1, "warn")])

    check_sql.execute(dbms, _FakeConnection(cursor), "check_proc", ["a", "b"], procedure=True)

    assert cursor.procedure_calls == [("check_proc", ["a", "b"])]


def test_mssql_procedure_is_executed_via_exec_statement() -> None:
    cursor = _FakeCursor([(1, "warn")])

    check_sql.execute("mssql", _FakeConnection(cursor), "check_proc", ["ignored"], procedure=True)

    assert cursor.executed == ["EXEC check_proc"]


def test_connection_is_closed_when_execution_fails() -> None:
    cursor = _FakeCursor([], fail=True)
    connection = _FakeConnection(cursor)

    with pytest.raises(RuntimeError):
        check_sql.execute("postgres", connection, "SELEC 1", [])

    assert cursor.closed and connection.closed


@pytest.mark.parametrize("number", [0, 1, 2, 3])
def test_result_without_levels_is_taken_as_state(number: int) -> None:
    assert check_sql.process_result(
        [(number, "message")], check_sql.MP_INF, check_sql.MP_INF, metrics=None, debug=False
    ) == (number, "message")


def test_single_column_result_uses_the_value_as_text() -> None:
    assert check_sql.process_result(
        [(2,)], check_sql.MP_INF, check_sql.MP_INF, metrics=None, debug=False
    ) == (2, "2")


def test_third_column_is_added_as_metric() -> None:
    assert check_sql.process_result(
        [(0, "ok", 42)], check_sql.MP_INF, check_sql.MP_INF, metrics="rows", debug=False
    ) == (0, "ok | rows=42")


def test_missing_metric_column_is_ignored() -> None:
    assert check_sql.process_result(
        [(0, "ok")], check_sql.MP_INF, check_sql.MP_INF, metrics="rows", debug=False
    ) == (0, "ok")


def test_missing_metric_column_raises_in_debug_mode() -> None:
    with pytest.raises(IndexError):
        check_sql.process_result(
            [(0, "ok")], check_sql.MP_INF, check_sql.MP_INF, metrics="rows", debug=True
        )


@pytest.mark.parametrize(
    "result, message",
    [
        pytest.param([], "SQL statement/procedure returned no data", id="no rows"),
        pytest.param([(7, "x")], "<7> is not a state, and no levels given", id="not a state"),
    ],
)
def test_unusable_result_is_unknown(
    result: list[tuple[object, ...]], message: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        check_sql.process_result(
            result, check_sql.MP_INF, check_sql.MP_INF, metrics=None, debug=False
        )

    assert (exit_info.value.code, capsys.readouterr().out) == (3, f"{message}\n")


@pytest.mark.usefixtures("restore_root_logging")
def test_open_ended_levels_are_parsed() -> None:
    args = check_sql.parse_args([*_REQUIRED_ARGS, "--sql-statement", "x", "-w", "1:", "-c", ":5"])

    assert (args.warning, args.critical) == ((1.0, float("inf")), (float("-inf"), 5.0))


@pytest.mark.usefixtures("restore_root_logging")
def test_escaped_newlines_and_semicolons_in_statement_are_restored() -> None:
    args = check_sql.parse_args([*_REQUIRED_ARGS, "--sql-statement", r"SELECT 1\;\nSELECT 2"])

    assert args.cmd == "SELECT 1;\nSELECT 2"


@pytest.mark.usefixtures("restore_root_logging")
def test_input_values_are_split_at_commas() -> None:
    args = check_sql.parse_args([*_REQUIRED_ARGS, "--sql-statement", "p", "-o", "-i", "a,b"])

    assert (args.procedure, args.input) == (True, ["a", "b"])


@pytest.mark.usefixtures("restore_root_logging")
def test_very_verbose_mssql_enables_tds_dump(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TDSDUMP", "")
    monkeypatch.delenv("TDSDUMP")

    check_sql.parse_args([*_REQUIRED_ARGS, "--sql-statement", "x", "-d", "mssql", "-vv"])

    assert os.environ["TDSDUMP"] == "stdout"


@pytest.mark.usefixtures("restore_root_logging")
def test_sqlanywhere_without_binaries_is_unknown(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        check_sql.main([*_REQUIRED_ARGS, "--sql-statement", "x", "-d", "sqlanywhere"])

    assert exit_info.value.code == 3
    assert capsys.readouterr().out.startswith(
        "ERROR: SQL Anywhere binaries weren't found on your $PATH"
    )
