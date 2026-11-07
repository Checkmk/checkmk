#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""EC History mongo backend"""

import logging
import os
import re
from unittest import mock

import pytest

import cmk.ec.export as ec
from cmk.ccc.hostaddress import HostName
from cmk.ec.history import History
from cmk.ec.history_file import FileHistory
from cmk.ec.history_mongo import filters_to_mongo_query, MongoDBHistory
from cmk.ec.main import StatusTableEvents, StatusTableHistory
from cmk.ec.query import OperatorName, QueryFilter, QueryGET, StatusTable

from .helpers import (
    EVENTS_WITH_CONTACT_GROUPS,
    EVENTS_WITH_FIRST_TIMES,
    LIST_FILTER_CASES,
    TIME_FILTER_CASES,
)

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


EVENT_DEFAULTS = dict(StatusTableEvents.columns)


def history_query(history: History, *filter_lines: str) -> QueryGET:
    logger = logging.getLogger("cmk.mkeventd")
    return QueryGET(
        lambda _name: StatusTableHistory(logger, history),
        ["GET history", "Columns: event_text", *filter_lines],
        logger,
    )


def mongo_query_for(history: FileHistory, *filter_lines: str) -> dict[str, object]:
    """The MongoDB query for filters parsed like for any history, without needing a MongoDB"""
    return filters_to_mongo_query(history_query(history, *filter_lines).filters, EVENT_DEFAULTS)


def or_missing(key: str, conditions: dict[str, object]) -> dict[str, object]:
    """The conditions or no value, e.g. for an event without the field, i.e. with its default"""
    return {"$or": [conditions, {key: None}]}


@pytest.mark.parametrize(
    "filter_line, expected",
    [
        pytest.param("Filter: event_text = disk",  {"event.text": "disk"},                                    id="equal"),
        pytest.param("Filter: event_text = ",      or_missing("event.text", {"event.text": ""}),               id="equal to the default"),
        pytest.param("Filter: event_text != disk", or_missing("event.text", {"event.text": {"$ne": "disk"}}),  id="not equal"),
        pytest.param("Filter: event_text >= m",    {"event.text": {"$gte": "m"}},                             id="greater or equal"),
        pytest.param("Filter: event_count < 5",    or_missing("event.count", {"event.count": {"$lt": 5}}),     id="selecting the default"),
        pytest.param("Filter: history_who <= m",   {"who": {"$lte": "m"}},                                    id="history column, never missing"),
        pytest.param("Filter: history_line > 5",   {"_id": {"$gt": 5}},                                       id="history line"),
    ],
)  # fmt: skip
def test_filter_becomes_mongo_query(
    history: FileHistory, filter_line: str, expected: dict[str, object]
) -> None:
    assert mongo_query_for(history, filter_line) == expected


# MongoDB's regexes are PCRE's, which understand only some of ours alike and fold case
# differently, it rejects a regex with a NUL, and its "in" respects case.
@pytest.mark.parametrize(
    "filter_spec",
    [
        pytest.param(r"~ \d",            id="class escape"),
        pytest.param("~ a{2}",           id="counted repetition"),
        pytest.param("~ (?i)a",          id="flag"),
        pytest.param("~ [:alpha:]",      id="POSIX syntax for PCRE"),
        pytest.param("!~~ [^a]",         id="negated class folding case"),
        pytest.param("~ a\0b",           id="NUL"),
        pytest.param("=~ a\0b",          id="NUL ignoring case"),
        pytest.param("in a b",           id="in"),
    ],
)  # fmt: skip
def test_filter_mongodb_cant_apply_like_we_do_is_left_out(
    history: FileHistory, filter_spec: str
) -> None:
    assert mongo_query_for(history, f"Filter: event_text {filter_spec}") == {}


TEXT = "event.text"
KELVIN_SIGN = "K"
LONG_S = "ſ"


# MongoDB doesn't fold case itself, the alternatives are the characters which Python's re
# takes as equal, e.g. "s" and the long s, and [^\n] and (?=\n?\z) are Python's "." and "$".
@pytest.mark.parametrize(
    "filter_spec, expected",
    [
        pytest.param(r"~ a.b\.c",          {TEXT: {"$regex": r"a[^\n]b\.c"}},                         id="regex"),
        pytest.param("~~ k.s",             {TEXT: {"$regex": rf"(K|k|{KELVIN_SIGN})[^\n](S|s|{LONG_S})"}}, id="regex ignoring case"),
        pytest.param("=~ a.b",             {TEXT: {"$regex": r"\A(A|a)\.(B|b)\z"}},                   id="equality ignoring case"),
        pytest.param("!~ a.b",             or_missing(TEXT, {TEXT: {"$not": re.compile(r"a[^\n]b")}}), id="negated regex"),
        pytest.param("!~~ a",              or_missing(TEXT, {TEXT: {"$not": re.compile("(A|a)")}}),   id="negated regex ignoring case"),
        pytest.param("!=~ a",              or_missing(TEXT, {TEXT: {"$not": re.compile(r"\A(A|a)\z")}}), id="negated equality ignoring case"),
        pytest.param(r"~ ^db[0-9]+\.x$",   {TEXT: {"$regex": r"^db[0-9]+\.x(?=\n?\z)"}},              id="anchors, class and quantifier"),
        pytest.param("~~ ^db[0-9]",        {TEXT: {"$regex": "^(D|d)(B|b)[0-9]"}},                   id="class not folding case, ignoring case"),
        pytest.param("~~ [ks]+",           {TEXT: {"$regex": f"(?:[ks]|K|S|{LONG_S}|{KELVIN_SIGN})+"}}, id="class folding case"),
        pytest.param("!~ (disk|cpu)s*?",   or_missing(TEXT, {TEXT: {"$not": re.compile("(disk|cpu)s*?")}}), id="negated group and lazy quantifier"),
    ],
)  # fmt: skip
def test_regex_filter_becomes_an_exact_mongo_regex(
    history: FileHistory, filter_spec: str, expected: dict[str, object]
) -> None:
    assert mongo_query_for(history, f"Filter: event_text {filter_spec}") == expected


def test_all_filters_on_the_same_column_end_up_in_the_mongo_query(history: FileHistory) -> None:
    assert mongo_query_for(history, "Filter: history_line >= 2", "Filter: history_line <= 4") == {
        "_id": {"$gte": 2},
        "$and": [{"_id": {"$lte": 4}}],
    }


DOWNTIME = "event.host_in_downtime"


@pytest.mark.parametrize(
    "filter_line, expected",
    [
        pytest.param("Filter: event_host_in_downtime = 1",  {DOWNTIME: {"$in": [True]}},                        id="true"),
        pytest.param("Filter: event_host_in_downtime = 0",  or_missing(DOWNTIME, {DOWNTIME: {"$in": [False]}}), id="false or missing"),
        pytest.param("Filter: event_host_in_downtime != 0", or_missing(DOWNTIME, {DOWNTIME: {"$in": [True]}}),  id="not false or None"),
        pytest.param("Filter: event_host_in_downtime > 1",  {DOWNTIME: {"$in": []}},                            id="nothing"),
    ],
)  # fmt: skip
def test_bool_filter_becomes_mongo_query_for_the_booleans_it_selects(
    history: FileHistory, filter_line: str, expected: dict[str, object]
) -> None:
    """MongoDB stores booleans, which equal no number"""
    assert mongo_query_for(history, filter_line) == expected


@pytest.mark.parametrize(
    "operator_name, expected",
    [
        pytest.param("=",  {"$gte": 5, "$lt": 6},           id="equal"),
        pytest.param("!=", {"$not": {"$gte": 5, "$lt": 6}}, id="not equal"),
        pytest.param("<",  {"$lt": 5},                      id="less"),
        pytest.param("<=", {"$lt": 6},                      id="less or equal"),
        pytest.param(">",  {"$gte": 6},                     id="greater"),
        pytest.param(">=", {"$gte": 5},                     id="greater or equal"),
    ],
)  # fmt: skip
def test_time_filter_becomes_mongo_query_for_the_truncated_time(
    history: FileHistory, operator_name: OperatorName, expected: dict[str, object]
) -> None:
    """Like Livestatus, which truncates the times to integers, see TIME_FILTER_CASES"""
    assert mongo_query_for(history, f"Filter: history_time {operator_name} 5") == {"time": expected}


@requires_mongodb
@pytest.mark.parametrize("value, expected_texts", [("0", {"no"}), ("1", {"yes"})])
def test_bool_filter_value_is_parsed_like_an_int_in_livestatus(
    history_mongo: MongoDBHistory, value: str, expected_texts: set[str]
) -> None:
    history_mongo.add(event=ec.Event(text="no", host_in_downtime=False), what="NEW")
    history_mongo.add(event=ec.Event(text="yes", host_in_downtime=True), what="NEW")
    query = history_query(history_mongo, f"Filter: event_host_in_downtime = {value}")

    _header, *rows = query.table.query(query)

    assert {text for (text,) in rows} == expected_texts


@requires_mongodb
@pytest.mark.parametrize("operator_name, argument, expected_texts", TIME_FILTER_CASES)
def test_time_filter_compares_the_truncated_time_like_livestatus(
    history_mongo: MongoDBHistory, operator_name: str, argument: str, expected_texts: set[str]
) -> None:
    for event in EVENTS_WITH_FIRST_TIMES:
        history_mongo.add(event=event, what="NEW")
    query = history_query(history_mongo, f"Filter: event_first {operator_name} {argument}")

    _header, *rows = query.table.query(query)

    assert {text for (text,) in rows} == expected_texts


@requires_mongodb
@pytest.mark.parametrize(
    "filter_line, expected_texts",
    [
        pytest.param("Filter: event_core_host = ",  {"orphan"},                              id="no value counts as the default"),
        pytest.param("Filter: event_host in WEB01", {"web01"},                               id="in ignores case"),
        pytest.param("Filter: event_text =~ KAPI",  {"kapı"},                                id="equality ignoring case"),
        pytest.param("Filter: event_text !=~ KAPI", {"orphan", "web01", "٣", "Bärlauch"},    id="negated equality ignoring case"),
        pytest.param("Filter: event_text ~~ PI",    {"kapı"},                                id="regex ignoring case"),
        pytest.param("Filter: event_text !~~ PI",   {"orphan", "web01", "٣", "Bärlauch"},    id="negated regex ignoring case"),
        pytest.param("Filter: event_text ~ B.r",    {"Bärlauch"},                            id="dot for a character of several bytes"),
        pytest.param("Filter: event_text !~ B.r",   {"orphan", "web01", "kapı", "٣"},        id="negated regex"),
        pytest.param(r"Filter: event_text ~ ^\d$",  {"٣"},                                   id="regex"),
        pytest.param("Filter: event_text ~ ^w.b[0-9]+$",   {"web01"},                        id="anchors, class and quantifier"),
        pytest.param("Filter: event_text ~~ ^WEB[0-9]+$",  {"web01"},                        id="class not folding case, ignoring case"),
        pytest.param("Filter: event_text ~~ ^[A-Z]AP",     {"kapı"},                         id="class folding case"),
        pytest.param("Filter: event_text !~~ ^[A-Z]AP",    {"orphan", "web01", "٣", "Bärlauch"}, id="negated regex with a class folding case"),
        pytest.param("Filter: event_text !~ ^(kapı|٣)$",   {"orphan", "web01", "Bärlauch"},  id="negated group"),
        pytest.param("Filter: event_text ~ [:alpha:]",     {"orphan", "kapı", "Bärlauch"},   id="POSIX syntax for PCRE"),
        pytest.param("Filter: event_text ~ \0",            set(),                            id="NUL"),
        pytest.param("Filter: event_text ~~ " + "x" * 7000, set(),                           id="too long with the case variants"),
    ],
)  # fmt: skip
def test_filter_selects_like_for_the_events(
    history_mongo: MongoDBHistory, filter_line: str, expected_texts: set[str]
) -> None:
    # Like an archived orphan, i.e. an event that no rule matched, it has no core host.
    history_mongo.add(event=ec.Event(text="orphan", host=HostName("orphan")), what="ORPHANED")
    history_mongo.add(
        event=ec.Event(text="web01", host=HostName("web01"), core_host=HostName("web01")),
        what="NEW",
    )
    for text in ("kapı", "٣", "Bärlauch"):
        history_mongo.add(
            event=ec.Event(text=text, host=HostName("other"), core_host=HostName("other")),
            what="NEW",
        )
    query = history_query(history_mongo, filter_line)

    _header, *rows = query.table.query(query)

    assert {text for (text,) in rows} == expected_texts


# MongoDB can't compile some of the regexes we translate for it, though they are much shorter
# than its limit of 32764 bytes, e.g. one with a group of case variants for each character.
@requires_mongodb
@pytest.mark.parametrize(
    "filter_spec",
    [
        pytest.param("=~ " + "A" * 5000,                 id="too large with the case variants"),
        pytest.param("~ ^" + "[ab]" * 2500,              id="too large with the classes"),
        pytest.param("~ " + "(" * 300 + "a" + ")" * 300, id="too deeply nested"),
    ],
)  # fmt: skip
def test_filter_with_a_regex_mongodb_cant_compile_works(
    history_mongo: MongoDBHistory, filter_spec: str
) -> None:
    for text in ("a" * 5000, "other"):
        history_mongo.add(event=ec.Event(text=text), what="NEW")
    query = history_query(history_mongo, f"Filter: event_text {filter_spec}")

    _header, *rows = query.table.query(query)

    assert rows == [["a" * 5000]]


@requires_mongodb
def test_limit_counts_only_the_entries_the_filters_select(history_mongo: MongoDBHistory) -> None:
    for text in ("Bärlauch", "other", "newest"):
        history_mongo.add(event=ec.Event(text=text), what="NEW")
    query = history_query(history_mongo, "Filter: event_text ~~ ^b", "Limit: 1")

    _header, *rows = query.table.query(query)

    assert rows == [["Bärlauch"]]


GROUPS = "event.contact_groups"


def contains(element: str) -> dict[str, object]:
    return {GROUPS: {"$elemMatch": {"$eq": element}}}


def lacks(element: str) -> dict[str, object]:
    return {"$nor": [contains(element)]}


@pytest.mark.parametrize(
    "operator_name, argument, expected",
    [
        pytest.param("=",   "",       or_missing(GROUPS, {GROUPS: {"$in": [None, [], [""]]}}), id="empty"),
        pytest.param("=",   "admins", {GROUPS: {"$in": []}},                                  id="equal tests only for emptiness"),
        pytest.param("!=",  "",       {GROUPS: {"$nin": [None, [], [""]]}},                   id="not empty"),
        pytest.param("!=",  "admins", {GROUPS: {"$in": []}},                                  id="not equal tests only for emptiness"),
        pytest.param(">=",  "admins", contains("admins"),                                     id="contains"),
        pytest.param(">=",  "",       {"$expr": mock.ANY},                                    id="contains an empty string before the last element"),
        pytest.param("<",   "admins", or_missing(GROUPS, lacks("admins")),                    id="doesn't contain"),
        pytest.param("=~",  "admins", {GROUPS: {"$in": []}},                                  id="equal ignoring case never holds"),
        pytest.param("!=~", "admins", {GROUPS: {"$in": []}},                                  id="not equal ignoring case never holds"),
        pytest.param("<=",  "admins", {},                                                     id="contains ignoring case, left out"),
        pytest.param(">",   "admins", {},                                                     id="doesn't contain ignoring case, left out"),
        pytest.param("~",   "^adm",   {},                                                     id="regex, left out"),
        pytest.param("!~~", "^adm",   {},                                                     id="regex ignoring case, left out"),
    ],
)  # fmt: skip
def test_list_column_filter_becomes_mongo_query_like_in_livestatus(
    history: FileHistory, operator_name: OperatorName, argument: str, expected: dict[str, object]
) -> None:
    """See LIST_FILTER_CASES"""
    filter_line = f"Filter: event_contact_groups {operator_name} {argument}"

    assert mongo_query_for(history, filter_line) == expected


@requires_mongodb
@pytest.mark.parametrize("operator_name, argument, expected_texts", LIST_FILTER_CASES)
def test_list_column_filter_works_like_in_livestatus(
    history_mongo: MongoDBHistory, operator_name: str, argument: str, expected_texts: set[str]
) -> None:
    for event in EVENTS_WITH_CONTACT_GROUPS:
        history_mongo.add(event=event, what="NEW")
    query = history_query(history_mongo, f"Filter: event_contact_groups {operator_name} {argument}")

    _header, *rows = query.table.query(query)

    assert {text for (text,) in rows} == expected_texts


def test_filters_to_mongo_query_Exception() -> None:
    """Exception on a column name not starting with "event_" or "history_"."""

    with pytest.raises(Exception, match="not implemented for MongoDB"):
        filters_to_mongo_query(
            [
                QueryFilter(
                    column_name="wrong_column_name",
                    operator_name="=",
                    predicate=lambda _: True,
                    argument="test_event",
                )
            ],
            EVENT_DEFAULTS,
        )
