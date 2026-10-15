#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""EC History mongo backend"""

import logging
import os
import re

import pytest

from cmk.utils.hostaddress import HostName

import cmk.ec.export as ec
from cmk.ec.history_mongo import filters_to_mongo_query, MongoDBHistory
from cmk.ec.main import StatusTableHistory
from cmk.ec.query import OperatorName, QueryFilter, QueryGET, StatusTable

requires_mongodb = pytest.mark.skipif(
    os.getenv("MONGODB_CONNECTION_STRING") is None,
    reason="""MONGODB_CONNECTION_STRING env var is not set.
    Set it to any value(1 or True) to use the default host: "localhost", port: 27017.
    Or use real mongodb connection string. E.g.:
    MONGODB_CONNECTION_STRING="mongodb://<some_host>:<some_port>" """,
)


@requires_mongodb
def test_pymongo_add_get(history_mongo: MongoDBHistory) -> None:
    """Add 2 documents to history, get filtered result with 1 document."""

    event1 = ec.Event(host=HostName("ABC1"), text="Event1 text", core_host=HostName("ABC"))
    event2 = ec.Event(host=HostName("ABC2"), text="Event2 text", core_host=HostName("ABC"))

    history_mongo.add(event=event1, what="NEW")
    history_mongo.add(event=event2, what="NEW")

    logger = logging.getLogger("cmk.mkeventd")

    def get_table(name: str) -> StatusTable:
        assert name == "history"
        return StatusTableHistory(logger, history_mongo)

    query = QueryGET(
        get_table,
        ["GET history", "Columns: history_what host_name", "Filter: event_host = ABC1"],
        logger,
    )

    query_result = history_mongo.get(query)

    (row,) = query_result
    column_index = get_table("history").column_names.index
    assert row[column_index("history_what")] == "NEW"
    assert row[column_index("event_host")] == "ABC1"


@requires_mongodb
def test_get_with_zero_limit_does_not_fetch_the_whole_history(
    history_mongo: MongoDBHistory,
) -> None:
    for text in ("one", "two", "three"):
        history_mongo.add(event=ec.Event(text=text), what="NEW")
    logger = logging.getLogger("cmk.mkeventd")
    query = QueryGET(
        lambda _name: StatusTableHistory(logger, history_mongo), ["GET history", "Limit: 0"], logger
    )

    rows = history_mongo.get(query)

    assert len(list(rows)) <= 1


@requires_mongodb
def test_history_query_applies_all_filters_on_the_same_column(
    history_mongo: MongoDBHistory,
) -> None:
    for event_id in (1, 2, 3):
        history_mongo.add(event=ec.Event(id=event_id, text=f"event {event_id}"), what="NEW")
    logger = logging.getLogger("cmk.mkeventd")
    table = StatusTableHistory(logger, history_mongo)
    query = QueryGET(
        lambda _name: table,
        ["GET history", "Columns: event_id", "Filter: event_id >= 2", "Filter: event_id <= 2"],
        logger,
    )

    _header, *rows = table.query(query)

    assert rows == [[2]]


def test_filters_to_mongo_query() -> None:
    """Filters become proper mongo query"""

    filters = [
        QueryFilter(
            column_name="event_text",
            operator_name="=",
            predicate=lambda x: True,
            argument="test_event",
        ),
        QueryFilter(
            column_name="event_time",
            operator_name="<",
            predicate=lambda x: True,
            argument=1234,
        ),
        QueryFilter(
            column_name="event_delay_until",
            operator_name="<=",
            predicate=lambda x: True,
            argument=120,
        ),
        QueryFilter(
            column_name="event_comment",
            operator_name="~",
            predicate=lambda x: True,
            argument="test",
        ),
        QueryFilter(
            column_name="event_location",
            operator_name="=~",
            predicate=lambda x: True,
            argument="seattle",
        ),
        QueryFilter(
            column_name="event_phase",
            operator_name="~~",
            predicate=lambda x: True,
            argument="test",
        ),
        QueryFilter(
            column_name="event_owner",
            operator_name="in",
            predicate=lambda x: True,
            argument=["foo", "bar"],
        ),
        QueryFilter(
            column_name="history_owner",
            operator_name="in",
            predicate=lambda x: True,
            argument="foobar",
        ),
        QueryFilter(
            column_name="history_line",
            operator_name="in",
            predicate=lambda x: True,
            argument="some text",
        ),
    ]

    expected_output = {
        "event.text": "test_event",
        "event.time": {"$lt": 1234},
        "event.delay_until": {"$lte": 120},
        "event.comment": {"$regex": "test", "$options": ""},
        "event.location": {"$regex": re.compile(r"\Aseattle(?![\s\S])", re.IGNORECASE)},
        "event.phase": {"$regex": "test", "$options": "i"},
        "event.owner": {"$in": ["foo", "bar"]},
        "owner": {"$in": "foobar"},
        "_id": {"$in": "some text"},
    }
    assert filters_to_mongo_query(filters) == expected_output


def test_all_filters_on_the_same_column_end_up_in_the_mongo_query() -> None:
    filters = [
        QueryFilter(
            column_name="event_id", operator_name=">=", predicate=lambda _: True, argument=2
        ),
        QueryFilter(
            column_name="event_id", operator_name="<=", predicate=lambda _: True, argument=4
        ),
    ]

    assert filters_to_mongo_query(filters) == {
        "event.id": {"$gte": 2},
        "$and": [{"event.id": {"$lte": 4}}],
    }


def mongo_filter_for(operator_name: OperatorName, argument: str) -> object:
    query_filter = QueryFilter(
        column_name="event_text",
        operator_name=operator_name,
        predicate=lambda _: True,
        argument=argument,
    )
    return filters_to_mongo_query([query_filter])["event.text"]


def mongo_regex_for(operator_name: OperatorName, argument: str) -> re.Pattern[str]:
    match mongo_filter := mongo_filter_for(operator_name, argument):
        case {"$regex": re.Pattern() as regex}:
            return regex
        case _:
            raise AssertionError(f"no regex in MongoDB filter {mongo_filter!r}")


# fmt: off
@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param("a.b",   True,  id="same value"),
        pytest.param("A.B",   True,  id="value differs in case"),
        pytest.param("axb",   False, id="value matches the argument only as a regex"),
        pytest.param("xa.bx", False, id="value contains the argument"),
        pytest.param("a.b\n", False, id="value has a trailing newline"),
    ],
)
# fmt: on
def test_case_insensitive_equality_filter_matches_only_the_whole_value_ignoring_case(
    value: str, expected: bool
) -> None:
    regex = mongo_regex_for("=~", "a.b")

    assert bool(regex.search(value)) is expected


def test_negated_case_insensitive_equality_filter_negates_the_same_regex() -> None:
    assert mongo_filter_for("!=~", "a.b") == {"$not": mongo_regex_for("=~", "a.b")}


# fmt: off
@pytest.mark.parametrize(
    "operator_name, expected",
    [
        pytest.param("!=",  {"$ne": "a.b"},                             id="not equal"),
        pytest.param("!~",  {"$not": re.compile("a.b")},                id="regex does not match"),
        pytest.param("!~~", {"$not": re.compile("a.b", re.IGNORECASE)}, id="regex does not match ignoring case"),
    ],
)
# fmt: on
def test_negated_filter_becomes_negated_mongo_query(
    operator_name: OperatorName, expected: dict[str, object]
) -> None:
    assert mongo_filter_for(operator_name, "a.b") == expected


def test_filters_to_mongo_query_Exception() -> None:
    """Exception on a column name not starting with "event_" or "history_"."""

    with pytest.raises(Exception):
        filters_to_mongo_query(
            [
                QueryFilter(
                    column_name="wrong_column_name",
                    operator_name="=",
                    predicate=lambda x: True,
                    argument="test_event",
                )
            ]
        )
