#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import datetime
import os
import time
from collections.abc import Iterable, Mapping, Sequence
from logging import Logger
from typing import Any, Literal

from .config import Config
from .event import Event
from .history import _log_event, History
from .query import Columns, QueryFilter, QueryGET
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
        history_columns: Columns,
    ) -> None:
        self._settings = settings
        self._config = config
        self._logger = logger
        self._event_columns = event_columns
        self._mongodb = MongoDB()
        self._reload_configuration_mongodb()

    def flush(self) -> None:
        self._mongodb.db.ec_archive.drop()

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

    def get(self, query: QueryGET) -> Iterable[Sequence[object]]:
        history_entries = []

        if not self._mongodb.connection:
            _connect_mongodb(self._settings, self._mongodb)

        # Construct the mongodb filtering specification. We could fetch all information
        # and do filtering on this data, but this would be way too inefficient.
        mongo_query = filters_to_mongo_query(query.filters)

        result = self._mongodb.db.ec_archive.find(mongo_query).sort("time", -1)

        # Might be used for debugging / profiling
        # open(cmk.utils.paths.omd_root + '/var/log/check_mk/ec_history_debug.log', 'a').write(
        #    pprint.pformat(filters) + '\n' + pprint.pformat(result.explain()) + '\n')

        if query.limit:
            result = result.limit(query.limit + 1)

        # now convert the MongoDB data structure to the eventd internal one
        for entry in result:
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
            history_entries.append(item)

        return history_entries

    def housekeeping(self) -> None:
        """Not needed in mongo since the lifetime of DB entries is taken care automatically."""

    def _reload_configuration_mongodb(self) -> None:
        """Configure the auto deleting indexes in the DB."""
        _update_mongodb_indexes(self._settings, self._mongodb)
        _update_mongodb_history_lifetime(self._settings, self._config, self._mongodb)

    def close(self) -> None:
        if self._mongodb.connection:
            self._mongodb.connection.close()
            self._mongodb.connection = None


def filters_to_mongo_query(
    filters: Iterable[QueryFilter],
) -> dict[str, str | dict[str, str]]:
    """Construct the mongodb filtering specification."""
    mongo_query = {}
    for f in filters:
        mongo_filter: str | dict[str, str] = {
            "=": f.argument,
            ">": {"$gt": f.argument},
            "<": {"$lt": f.argument},
            ">=": {"$gte": f.argument},
            "<=": {"$lte": f.argument},
            "~": {"$regex": f.argument, "$options": ""},
            "=~": {"$regex": f.argument, "$options": "mi"},
            "~~": {"$regex": f.argument, "$options": "i"},
            "in": {"$in": f.argument},
        }[f.operator_name]

        if f.column_name[:6] == "event_":
            mongo_query["event." + f.column_name[6:]] = mongo_filter
        elif f.column_name[:8] == "history_":
            key = f.column_name[8:]
            if key == "line":
                key = "_id"
            mongo_query[key] = mongo_filter
        else:
            raise Exception(f"Filter {f.column_name} not implemented for MongoDB")
    return mongo_query


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
    return result["dt_-1"]["expireAfterSeconds"]


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
    return ret["seq"]
