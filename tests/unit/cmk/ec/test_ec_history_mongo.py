#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""EC History mongo backend"""

from collections.abc import Callable
from typing import Any

import pytest

from cmk.ec.history_mongo import filters_to_mongo_query
from cmk.ec.query import OperatorName


def test_filters_to_mongo_query() -> None:
    """Filters become proper mongo query"""

    filters: list[tuple[str, OperatorName, Callable[[Any], bool], Any]] = [
        ("event_text", "=", lambda x: True, "test_event"),
        ("event_time", "<", lambda x: True, 1234),
        ("event_delay_until", "<=", lambda x: True, 120),
        ("event_comment", "~", lambda x: True, "test"),
        ("event_location", "=~", lambda x: True, "seattle"),
        ("event_phase", "~~", lambda x: True, "test"),
        ("event_owner", "in", lambda x: True, ["foo", "bar"]),
        ("history_owner", "in", lambda x: True, "foobar"),
        ("history_line", "in", lambda x: True, "some text"),
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
        filters_to_mongo_query([("wrong_column_name", "=", lambda x: True, "test_event")])
