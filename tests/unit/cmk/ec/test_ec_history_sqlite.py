#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import sqlite3
from typing import Literal

import pytest

import cmk.ec.export as ec
from cmk.ccc.hostaddress import HostName
from cmk.ec.history_sqlite import filters_to_sqlite_query, SQLiteHistory
from cmk.ec.main import StatusTableHistory
from cmk.ec.query import QueryFilter, QueryGET, StatusTable


def in_memory_db() -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE history(id INTEGER, text TEXT)")
    return con


def test_equal_operator_with_matching_lower_case_argument_returns_matching_lower_case_text() -> (
    None
):
    with in_memory_db() as con:
        con.execute("INSERT INTO history VALUES(0, 'test text')")
        con.execute("INSERT INTO history VALUES(1, 'wrong text')")
        con.execute("INSERT INTO history VALUES(2, 'TEST TEXT')")
        con.execute("INSERT INTO history VALUES(3, 'TeSt tExt')")
        con.execute("INSERT INTO history VALUES(4, 'test text')")

        (query, params) = filters_to_sqlite_query(
            [
                QueryFilter(
                    column_name="event_text",
                    operator_name="=",
                    predicate=lambda x: True,
                    argument="test text",
                )
            ]
        )

        result = con.execute(query, params)
        assert result.fetchall() == [(0, "test text"), (4, "test text")]


def test_equal_operator_with_unmatching_lower_case_argument_returns_empty_result() -> None:
    with in_memory_db() as con:
        (query, params) = filters_to_sqlite_query(
            [
                QueryFilter(
                    column_name="event_text",
                    operator_name="=",
                    predicate=lambda x: True,
                    argument="test text",
                )
            ]
        )

        result = con.execute(query, params)
        assert result.fetchall() == []


@pytest.mark.parametrize(
    "filter_value, expected_results",
    [
        ("TEST TEXT", [(0, "test text")]),
        ("test text", [(0, "test text")]),
        ("TeSt tExt", [(0, "test text")]),
    ],
)
def test_case_insensitive_equal_operator_with_matching_data_returns_matching_text(
    filter_value: str, expected_results: list[tuple[int, str]]
) -> None:
    with in_memory_db() as con:
        con.execute("INSERT INTO history VALUES(0, 'test text')")

        (query, params) = filters_to_sqlite_query(
            [
                QueryFilter(
                    column_name="event_text",
                    operator_name="=~",
                    predicate=lambda x: True,
                    argument=filter_value,
                )
            ]
        )

        result = con.execute(query, params)
        assert result.fetchall() == expected_results


@pytest.mark.parametrize(
    "filter_value, expected_results",
    [
        ("TEST TEXT", []),
        ("test text", []),
        ("TeSt tExt", []),
    ],
)
def test_case_insensitive_equal_operator_with_no_matching_data_returns_matching_text(
    filter_value: str, expected_results: list[tuple[int, str]]
) -> None:
    with in_memory_db() as con:
        (query, params) = filters_to_sqlite_query(
            [
                QueryFilter(
                    column_name="event_text",
                    operator_name="=~",
                    predicate=lambda x: True,
                    argument=filter_value,
                )
            ]
        )

        result = con.execute(query, params)
        assert result.fetchall() == expected_results


Operator = Literal[">", "<", ">=", "<="]


@pytest.mark.parametrize(
    "operator, filter_value, expected_results",
    [
        (">", 3, [(4, "value4"), (5, "value5")]),
        ("<", 3, [(0, "value0"), (1, "value1"), (2, "value2")]),
        (">=", 3, [(3, "value3"), (4, "value4"), (5, "value5")]),
        ("<=", 3, [(0, "value0"), (1, "value1"), (2, "value2"), (3, "value3")]),
    ],
)
def test_case_comparative_operator_with_matching_adjacent_data_returns_matching_text(
    operator: Operator,
    filter_value: int,
    expected_results: list[tuple[int, str]],
) -> None:
    with in_memory_db() as con:
        con.execute("INSERT INTO history VALUES(0, 'value0')")
        con.execute("INSERT INTO history VALUES(1, 'value1')")
        con.execute("INSERT INTO history VALUES(2, 'value2')")
        con.execute("INSERT INTO history VALUES(3, 'value3')")
        con.execute("INSERT INTO history VALUES(4, 'value4')")
        con.execute("INSERT INTO history VALUES(5, 'value5')")

        (query, params) = filters_to_sqlite_query(
            [
                QueryFilter(
                    column_name="event_id",
                    operator_name=operator,
                    predicate=lambda x: True,
                    argument=filter_value,
                )
            ]
        )

        result = con.execute(query, params)
        assert result.fetchall() == expected_results


@pytest.mark.parametrize(
    "filter_value, expected_results",
    [
        (("hello",), [(0, "hello"), (1, "hello"), (2, "hello")]),
        (("world",), [(3, "world")]),
        (("hello", "world"), [(0, "hello"), (1, "hello"), (2, "hello"), (3, "world")]),
        (("dropped",), [(5, "dropped")]),
    ],
)
def test_case_in_operator_with_some_matching_data_returns_matching_text(
    filter_value: str, expected_results: list[tuple[int, str]]
) -> None:
    with in_memory_db() as con:
        con.execute("INSERT INTO history VALUES(0, 'hello')")
        con.execute("INSERT INTO history VALUES(1, 'hello')")
        con.execute("INSERT INTO history VALUES(2, 'hello')")
        con.execute("INSERT INTO history VALUES(3, 'world')")
        con.execute("INSERT INTO history VALUES(4, 'connection dropped')")
        con.execute("INSERT INTO history VALUES(5, 'dropped')")

        (query, params) = filters_to_sqlite_query(
            [
                QueryFilter(
                    column_name="event_text",
                    operator_name="in",
                    predicate=lambda x: True,
                    argument=filter_value,
                )
            ]
        )

        result = con.execute(query, params)
        assert result.fetchall() == expected_results


def test_filters_to_sqlite_query_with_simple_equality_filter_has_correct_query() -> None:
    filters = [
        QueryFilter(
            column_name="event_text",
            operator_name="=",
            predicate=lambda x: True,
            argument="test_event",
        )
    ]

    assert filters_to_sqlite_query(filters) == (
        "SELECT * FROM history WHERE text = ?;",
        ["test_event"],
    )


def test_filters_to_sqlite_query_with_one_in_filter_has_one_placeholder_in_query() -> None:
    filters = [
        QueryFilter(
            column_name="event_text",
            operator_name="in",
            predicate=lambda x: True,
            argument=("test_event",),
        )
    ]

    assert filters_to_sqlite_query(filters) == (
        "SELECT * FROM history WHERE text in (?);",
        ["test_event"],
    )


def test_filters_to_sqlite_query_with_multiple_in_filters_has_multiple_matching_placeholders() -> (
    None
):
    filters = [
        QueryFilter(
            column_name="event_text",
            operator_name="in",
            predicate=lambda x: True,
            argument=("test_event", "test_event", "test_event"),
        )
    ]

    assert filters_to_sqlite_query(filters) == (
        "SELECT * FROM history WHERE text in (?,?,?);",
        ["test_event", "test_event", "test_event"],
    )


def test_filters_to_sqlite_query_with_less_than_and_greater_than_filters_have_correct_query() -> (
    None
):
    filters = [
        QueryFilter(
            column_name="event_time",
            operator_name="<",
            predicate=lambda x: True,
            argument=123456789,
        ),
        QueryFilter(
            column_name="event_time",
            operator_name=">",
            predicate=lambda x: True,
            argument=1234,
        ),
    ]
    assert filters_to_sqlite_query(filters) == (
        "SELECT * FROM history WHERE time < ? AND time > ?;",
        [123456789, 1234],
    )


def test_filters_to_sqlite_query_with_regex_and_case_insensitive_equality_filters_have_correct_query() -> (
    None
):
    filters = [
        QueryFilter(
            column_name="history_who",
            operator_name="~~",
            predicate=lambda x: True,
            argument="admin",
        ),
        QueryFilter(
            column_name="event_owner",
            operator_name="=~",
            predicate=lambda x: True,
            argument="user",
        ),
    ]

    assert filters_to_sqlite_query(filters) == (
        "SELECT * FROM history WHERE regexp_nocase(?, who) AND owner = ? COLLATE NOCASE;",
        ["admin", "user"],
    )


def test_filters_to_sqlite_query_with_no_filters_gives_a_simple_select_statement() -> None:
    assert filters_to_sqlite_query([]) == ("SELECT * FROM history  ;", [])


def test_filters_to_sqlite_query_raises_ValueError() -> None:
    """Wrong column name in filter raise ValueError."""

    wrong_filters = [
        QueryFilter(
            column_name="impossible_column_name",
            operator_name="=",
            predicate=lambda x: True,
            argument="test_event",
        )
    ]
    with pytest.raises(ValueError):
        filters_to_sqlite_query(wrong_filters)


def test_filters_to_sqlite_query_raises_KeyError() -> None:
    """Wrong operator name in filter raise KeyError."""

    wrong_filters = [
        QueryFilter(
            column_name="event_text",
            operator_name="=asdf or true;",  # type: ignore[arg-type]
            predicate=lambda x: True,
            argument="test_event",
        )
    ]
    with pytest.raises(KeyError):
        filters_to_sqlite_query(wrong_filters)


def test_basic_init_history_table(history_sqlite: SQLiteHistory) -> None:
    """Basic init in memory and history table exists."""

    cur = history_sqlite.conn.cursor()
    cur.row_factory = None
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='history';")
    assert cur.fetchall()[0] == ("history",)


def test_file_add_get(history_sqlite: SQLiteHistory) -> None:
    """Add 2 documents to history, get filtered result with 1 document."""

    event1 = ec.Event(
        host=HostName("ABC1"),
        text="Event1 text",
        core_host=HostName("ABC"),
        id=1,
        count=1,
        first=1.1,
        last=1.111,
        priority=100,
        host_in_downtime=False,
        contact_groups=("some string1", "another string1"),
    )
    event2 = ec.Event(
        host=HostName("ABC2"),
        text="Event2 text",
        core_host=HostName("ABC"),
        id=2,
        count=2,
        first=2.0,
        last=2.222,
        priority=200,
        host_in_downtime=True,
        contact_groups=("some string2", "another string2"),
    )

    history_sqlite.add(event=event1, what="NEW")
    history_sqlite.add(event=event2, what="NEW")

    logger = logging.getLogger("cmk.mkeventd")

    def get_table(name: str) -> StatusTable:
        assert name == "history"
        return StatusTableHistory(logger, history_sqlite)

    query = QueryGET(
        get_table,
        ["GET history", "Columns: history_what event_host", "Filter: event_host = ABC1"],
        logger,
    )

    query_result = history_sqlite.get(query)

    (row,) = query_result

    # check for several possible types: int, float, str, bool, list/tuple
    assert row["what"] == "NEW"  # type: ignore[call-overload]
    assert row["host"] == "ABC1"  # type: ignore[call-overload]
    assert row["id"] == 1  # type: ignore[call-overload]
    assert row["count"] == 1  # type: ignore[call-overload]
    assert row["first"] == 1.1  # type: ignore[call-overload]
    assert row["last"] == 1.111  # type: ignore[call-overload]
    assert row["priority"] == 100  # type: ignore[call-overload]
    assert row["host_in_downtime"] is False  # type: ignore[call-overload]
    assert row["contact_groups"] == ["some string1", "another string1"]  # type: ignore[call-overload]


def test_housekeeping(history_sqlite: SQLiteHistory) -> None:
    """Add 2 events to history, drop the older one."""

    event1 = ec.Event(host=HostName("ABC1"), text="Event1 text", core_host=HostName("ABC"))
    event2 = ec.Event(host=HostName("ABC2"), text="Event2 text", core_host=HostName("ABC"))
    history_sqlite.add(event=event1, what="NEW")
    history_sqlite.add(event=event2, what="NEW")

    with history_sqlite.conn as connection:
        cur = connection.cursor()
        cur.execute("SELECT count(*) FROM history;")
        assert cur.fetchone()["count(*)"] == 2

        cur.execute("UPDATE history set time = 123456 where host = 'ABC1'")
        history_sqlite.housekeeping()
        cur.execute("SELECT count(*) FROM history;")
        assert cur.fetchone()["count(*)"] == 1
