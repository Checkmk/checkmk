#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""EC History mongo backend"""

import pytest

from cmk.ec.history_mongo import filters_to_mongo_query
from cmk.ec.query import QueryFilter


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
