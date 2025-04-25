#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""EC History mongo backend"""

import logging
import os

import pytest

from cmk.ccc.hostaddress import HostName

import cmk.ec.export as ec
from cmk.ec.history_mongo import filters_to_mongo_query, MongoDBHistory
from cmk.ec.main import StatusTableHistory
from cmk.ec.query import QueryFilter, QueryGET, StatusTable


@pytest.mark.skipif(
    os.getenv("MONGODB_CONNECTION_STRING") is None,
    reason="""MONGODB_CONNECTION_STRING env var is not set.
    Set it to any value(1 or True) to use the default host: "localhost", port: 27017.
    Or use real mongodb connection string. E.g.:
    MONGODB_CONNECTION_STRING="mongodb://<some_host>:<some_port>" """,
)
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
        "event.location": {"$regex": "seattle", "$options": "mi"},
        "event.phase": {"$regex": "test", "$options": "i"},
        "event.owner": {"$in": ["foo", "bar"]},
        "owner": {"$in": "foobar"},
        "_id": {"$in": "some text"},
    }
    assert filters_to_mongo_query(filters) == expected_output


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
