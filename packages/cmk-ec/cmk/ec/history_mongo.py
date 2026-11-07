#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import contextlib
import datetime
import os
import re
import time
from collections.abc import Iterable, Mapping, Sequence
from logging import Logger
from typing import Any, Literal, override

from .config import Config
from .event import Event
from .history import _log_event, History
from .query import Columns, LIST_COLUMNS, QueryFilter, QueryGET, TIME_COLUMNS, time_conditions
from .regex_translation import pcre_regex, translated_text
from .settings import Settings

HistoryWhat = Literal[
    "ORPHANED",
    "NOCOUNT",
    "DELAYOVER",
    "EXPIRED",
    "COUNTREACHED",
    "COUNTFAILED",
    "UPDATE",
    "NEW",
    "DELETE",
    "EMAIL",
    "SCRIPT",
    "CANCELLED",
    "ARCHIVED",
    "AUTODELETE",
    "CHANGESTATE",
]


class MongoDBHistory(History):
    def __init__(
        self,
        settings: Settings,
        config: Config,
        logger: Logger,
        event_columns: Columns,
        history_columns: Columns,  # noqa: ARG002
    ) -> None:
        self._settings = settings
        self._config = config
        self._logger = logger.getChild("mongodb")
        self._event_columns = event_columns
        self._mongodb = MongoDB()
        self._reload_configuration_mongodb()

    @override
    def flush(self) -> None:
        self._mongodb.db.ec_archive.drop()

    @override
    def add(self, event: Event, what: HistoryWhat, who: str = "", addinfo: str = "") -> None:
        _log_event(self._config, self._logger, event, what, who, addinfo)
        if not self._mongodb.connection:
            _connect_mongodb(self._settings, self._mongodb)
        # We converted _id to be an auto incrementing integer. This makes the unique
        # index compatible to history_line of the file (which is handled as integer)
        # within mkeventd. It might be better to use the ObjectId() of MongoDB, but
        # for the first step, we use the integer index for simplicity
        now = time.time()
        self._mongodb.db.ec_archive.insert_one(
            {
                "_id": _mongodb_next_id(self._mongodb, "ec_archive_id"),
                "dt": datetime.datetime.fromtimestamp(now),
                "time": now,
                "event": event,
                "what": what,
                "who": who,
                "addinfo": addinfo,
            }
        )

    @override
    def get(self, query: QueryGET) -> Iterable[Sequence[object]]:
        if not self._mongodb.connection:
            _connect_mongodb(self._settings, self._mongodb)
        try:
            return self._get(query, query.filters)
        except OperationFailure as e:
            # MongoDB fails to compile some of the regexes we translate for it, e.g. too large
            # or too deeply nested ones, even far below its size limit. As we apply all
            # filters anyway, we leave out the regexes then.
            if e.code != _INVALID_REGEX:
                raise
            return self._get(
                query, [f for f in query.filters if f.operator_name not in _REGEX_OPERATORS]
            )

    def _get(self, query: QueryGET, filters: Iterable[QueryFilter]) -> list[Sequence[object]]:
        history_entries: list[Sequence[object]] = []
        # MongoDB selects at least the entries which the filters select, and we apply all
        # filters of the query, too, so they work like for the other histories. Only then
        # the limit counts.
        mongo_query = filters_to_mongo_query(filters, dict(self._event_columns))
        with self._mongodb.db.ec_archive.find(mongo_query).sort("time", -1) as result:
            for entry in result:
                # Like the other histories, at most one entry more than the limit
                if query.limit is not None and len(history_entries) > query.limit:
                    break
                item = [
                    entry["_id"],
                    entry["time"],
                    entry["what"],
                    entry["who"],
                    entry["addinfo"],
                ]
                for colname, defval in self._event_columns:
                    key = colname[6:]  # drop "event_"
                    item.append(entry["event"].get(key, defval))
                if query.filter_row(item):
                    history_entries.append(item)

        return history_entries

    @override
    def housekeeping(self) -> None:
        """Not needed in mongo since the lifetime of DB entries is taken care automatically."""

    def _reload_configuration_mongodb(self) -> None:
        """Configure the auto deleting indexes in the DB."""
        _update_mongodb_indexes(self._settings, self._mongodb)
        _update_mongodb_history_lifetime(self._settings, self._config, self._mongodb)

    @override
    def close(self) -> None:
        if self._mongodb.connection:
            self._mongodb.connection.close()
            self._mongodb.connection = None


def filters_to_mongo_query(
    filters: Iterable[QueryFilter], event_defaults: Mapping[str, object]
) -> dict[str, object]:
    """A query for at least the entries which the filters select, so the caller has to apply
    the filters, too. MongoDB can't do all of them like we do: It understands only some of our
    regexes alike, see _regex_filter_to_mongo_filter(), it compares "in" respecting case, and
    an event may lack a field, which counts as its default for us, see get(). So the query
    leaves out the filters it can't apply exactly, and it also selects the events without a
    field (or with None) if the filter selects the default (or None)."""
    mongo_query: dict[str, object] = {}
    further_conditions: list[dict[str, object]] = []
    for f in filters:
        if f.column_name[:6] == "event_":
            key = "event." + f.column_name[6:]
        elif f.column_name[:8] == "history_":
            key = f.column_name[8:]
            if key == "line":
                key = "_id"
        else:
            raise Exception(f"Filter {f.column_name} not implemented for MongoDB")
        # The default of an event column tells its type, the history columns have none.
        is_bool = isinstance(event_defaults.get(f.column_name), bool)
        conditions = _mongo_conditions(f, key, is_bool)
        if conditions is None:
            continue
        # The entries always have the history fields, see add().
        if f.column_name.startswith("event_") and (
            f.predicate(event_defaults[f.column_name]) or f.predicate(None)
        ):
            conditions = {"$or": [conditions, {key: None}]}
        # A key can occur only once in a query document, so further conditions
        # for the same key need an explicit $and.
        for name, condition in conditions.items():
            if name in mongo_query:
                further_conditions.append({name: condition})
            else:
                mongo_query[name] = condition
    if further_conditions:
        mongo_query["$and"] = further_conditions
    return mongo_query


def _mongo_conditions(f: QueryFilter, key: str, is_bool: bool) -> dict[str, object] | None:
    """The conditions of the query for the filter, None if MongoDB can't apply it exactly"""
    if f.column_name in LIST_COLUMNS:
        return _list_filter_to_mongo_query(f, key)
    if f.column_name in TIME_COLUMNS:
        return {key: _time_filter_to_mongo_filter(f)}
    if is_bool:
        return {key: _bool_filter_to_mongo_filter(f)}
    condition = query_filter_to_mongo_filter(f)
    return None if condition is None else {key: condition}


def query_filter_to_mongo_filter(f: QueryFilter) -> str | dict[str, object] | None:
    """The condition for a filter on a string or int column, None if MongoDB can't apply it
    exactly. For the ints, we compare their lower 32 bits like Livestatus, which are all the
    bits of the IDs and counts of events in practice."""
    match f.operator_name:
        case "=":
            argument: str = f.argument
            return argument
        case "!=":
            return {"$ne": f.argument}
        case "<":
            return {"$lt": f.argument}
        case ">=":
            return {"$gte": f.argument}
        case ">":
            return {"$gt": f.argument}
        case "<=":
            return {"$lte": f.argument}
        case "~" | "!~" | "=~" | "!=~" | "~~" | "!~~":
            return _regex_filter_to_mongo_filter(f)
        case "in":
            return None


def _regex_filter_to_mongo_filter(f: QueryFilter) -> dict[str, object] | None:
    """The condition for a regex filter or one ignoring case, None if MongoDB can't apply it
    exactly. Its regexes are PCRE's, which understand only some of ours alike and fold case
    differently, so only those go to it, translated without folding case, see pcre_regex().
    Exact, they work for the negated filters, too."""
    regex: str | None
    match f.operator_name:
        case "=~" | "!=~":
            # \z instead of $, which would match before a trailing newline, too
            regex = rf"\A{translated_text(f.argument, ignore_case=True)}\z"
        case "~" | "!~" | "~~" | "!~~":
            regex = pcre_regex(f.argument, ignore_case=f.operator_name in {"~~", "!~~"})
        case _:
            return None
    # MongoDB rejects a regex with a NUL. For the ones it can't compile, see get().
    if regex is None or "\0" in regex:
        return None
    return {"$not": re.compile(regex)} if f.operator_name.startswith("!") else {"$regex": regex}


# The operators of the filters which become regexes, see query_filter_to_mongo_filter()
_REGEX_OPERATORS = frozenset({"~", "!~", "=~", "!=~", "~~", "!~~"})

# MongoDB's error code for a regex it can't compile, e.g. "regular expression is too large"
_INVALID_REGEX = 51091


def _list_filter_to_mongo_query(f: QueryFilter, key: str) -> dict[str, object] | None:
    """The query for a filter on a list column, i.e. an array, which works like in Livestatus,
    see _list_predicate() in cmk.ec.query, None if MongoDB can't apply it exactly. A last
    empty string is no element, see _list_elements() there."""
    match f.operator_name:
        case "=" if f.argument == "":
            return {key: {"$in": [None, [], [""]]}}
        case "!=" if f.argument == "":
            return {key: {"$nin": [None, [], [""]]}}
        case ">=":
            return _has_element(key, f.argument)
        case "<":
            return {"$nor": [_has_element(key, f.argument)]}
        case "=" | "!=" | "=~" | "!=~":  # never hold
            return {key: {"$in": []}}
        case "<=" | ">" | "~" | "!~" | "~~" | "!~~" | "in":  # regexes or ignoring case
            return None


def _has_element(key: str, element: str) -> dict[str, object]:
    """The query for an array with the element, where an empty string counts only before the
    last element"""
    if element != "":
        return {key: {"$elemMatch": {"$eq": element}}}
    return {"$expr": _empty_string_before_the_last_element(key)}


def _empty_string_before_the_last_element(key: str) -> dict[str, object]:
    """An aggregation expression for an array whose first empty string isn't its last element"""
    array = f"${key}"
    first_empty_string = {"$indexOfArray": [array, ""]}
    return {
        "$cond": [
            {"$isArray": array},
            {
                "$and": [
                    {"$gte": [first_empty_string, 0]},
                    {"$lt": [first_empty_string, {"$subtract": [{"$size": array}, 1]}]},
                ]
            },
            False,
        ]
    }


_MONGO_COMPARISONS = {"<": "$lt", "<=": "$lte", ">": "$gt", ">=": "$gte"}


def _time_filter_to_mongo_filter(f: QueryFilter) -> dict[str, object]:
    """A filter on a time column, which compares the time truncated to an integer like
    Livestatus, see time_conditions() in cmk.ec.query"""
    conditions: dict[str, object] = {
        _MONGO_COMPARISONS[op]: value for op, value in time_conditions(f.operator_name, f.argument)
    }
    return {"$not": conditions} if f.operator_name == "!=" else conditions


def _bool_filter_to_mongo_filter(f: QueryFilter) -> dict[str, object]:
    """A filter on a bool column, which Livestatus has as an int column, so its value is an
    int, but in MongoDB, no boolean equals a number. So we select the booleans the filter
    selects."""
    return {"$in": [value for value in (False, True) if f.predicate(value)]}


try:
    import pymongo
    from pymongo.errors import OperationFailure

    pymongo_available = True
except ImportError:
    pymongo_available = False


class MongoDB:
    def __init__(self) -> None:
        self.connection: pymongo.MongoClient[Mapping[str, object]] | None = None
        self.db: Any = None


def _connect_mongodb(settings: Settings, mongodb: MongoDB) -> None:
    if not pymongo_available:
        raise Exception("Could not initialize MongoDB (Python-Modules are missing)")
    mongodb.connection = pymongo.MongoClient(*_mongodb_local_connection_opts(settings))
    mongodb.db = mongodb.connection[os.environ["OMD_SITE"]]


def _mongodb_local_connection_opts(settings: Settings) -> tuple[str | None, int | None]:
    ip, port = None, None
    with settings.paths.mongodb_config_file.value.open(encoding="utf-8") as f:
        for entry in f:
            if entry.startswith("bind_ip"):
                ip = entry.split("=")[1].strip()
            elif entry.startswith("port"):
                port = int(entry.split("=")[1].strip())
    return ip, port


def _get_mongodb_max_history_age(mongodb: MongoDB) -> int:
    result = mongodb.db.ec_archive.index_information()
    if "dt_-1" not in result or "expireAfterSeconds" not in result["dt_-1"]:
        return -1
    return result["dt_-1"]["expireAfterSeconds"]  # type: ignore[no-any-return]


def _update_mongodb_indexes(settings: Settings, mongodb: MongoDB) -> None:
    if not mongodb.connection:
        _connect_mongodb(settings, mongodb)
    result = mongodb.db.ec_archive.index_information()

    if "time_-1" not in result:
        mongodb.db.ec_archive.create_index([("time", pymongo.DESCENDING)])


def _update_mongodb_history_lifetime(settings: Settings, config: Config, mongodb: MongoDB) -> None:
    if not mongodb.connection:
        _connect_mongodb(settings, mongodb)

    if _get_mongodb_max_history_age(mongodb) == config["history_lifetime"] * 86400:
        return  # do not update already correct index

    with contextlib.suppress(OperationFailure):  # Ignore not existing index
        mongodb.db.ec_archive.drop_index("dt_-1")

    # Delete messages after x days
    mongodb.db.ec_archive.create_index(
        [("dt", pymongo.DESCENDING)],
        expireAfterSeconds=config["history_lifetime"] * 86400,
        unique=False,
    )


def _mongodb_next_id(mongodb: MongoDB, name: str, first_id: int = 0) -> int:
    ret = mongodb.db.counters.find_one_and_update(
        filter={"_id": name}, update={"$inc": {"seq": 1}}, new=True
    )

    if not ret:
        # Initialize the index!
        mongodb.db.counters.insert_one({"_id": name, "seq": first_id})
        return first_id
    return ret["seq"]  # type: ignore[no-any-return]
