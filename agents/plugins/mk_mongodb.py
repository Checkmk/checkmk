#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Monitor MongoDB on Linux

This agent plugin creates various sections out of the MongoDB server status information.
Important: 1) If MongoDB runs as single instance the agent data is assigned
              to the host same host where the plugin resides.

           2) If MongoDB is deployed as replica set the agent data is piggybacked
              to a different hostname, name after the replica set name.
              You have to create a new host in the monitoring system matching the
              replica set name, or use the piggyback translation rule to modify the
              hostname according to your needs.

It is possible to run this script with pymongo 2.5.2 (the version provided by
centos 7) but you can not connect to a MongoDB 4.0 server with authentication.
Pymongo 2.5.2 uses the auth mechanism ``MONGODB-CR`` but this auth mechanism
was removed with MongoDB 4.0. If you want to use mk_mongodb.py with
authentication and a MongoDB server 4.0 you will have to use a more recent
version of pymongo (at least 2.8).

"""

__version__ = "2.2.0i1"

import argparse
import configparser
import inspect
import json
import logging
import os
import sys
import time
from collections import defaultdict
from urllib.parse import quote_plus
from bson.json_util import DEFAULT_JSON_OPTIONS
DEFAULT_JSON_OPTIONS.datetime_representation = 0

PY2 = sys.version_info[0] == 2

try:
    from typing import Any, Callable, Dict, Iterable, Union
except ImportError:
    pass


try:
    import pymongo  # type: ignore[import] # pylint: disable=import-error
    import pymongo.errors  # type: ignore[import] # pylint: disable=import-error
    from bson.json_util import dumps  # type: ignore[import]
except ImportError:
    sys.stdout.write("<<<mongodb_instance:sep(9)>>>\n")
    sys.stdout.write(
        "error\tpymongo library is not installed. Please install it on the monitored system "
        "(for Python 3 use: 'pip3 install pymongo', for Python 2 use 'pip install pymongo')\n"
    )
    sys.exit(1)


MK_VARDIR = os.environ.get("MK_VARDIR")
PYMONGO_VERSION = tuple(int(i) for i in pymongo.version.split("."))


def get_database_info(client):
    if inspect.ismethod(client.list_database_names):
        db_names = client.list_database_names()
    elif inspect.ismethod(client.database_names):
        db_names = client.database_names()
    else:
        db_names = []

    databases = defaultdict(dict)  # type: Dict[str, Dict[str, Any]]
    for name in db_names:
        database = client[name]
        databases[name]["collections"] = list(get_collection_names(database))
        databases[name]["stats"] = database.command("dbstats")
        databases[name]["collstats"] = {}
        for collection in databases[name]["collections"]:
            databases[name]["collstats"][collection] = database.command("collstats", collection)
    return databases


def get_collection_names(database):  # type:(pymongo.database.Database) -> Iterable[str]
    if PYMONGO_VERSION <= (3, 6, 0):
        collection_names = database.collection_names()
    else:
        collection_names = database.list_collection_names()

    for collection_name in collection_names:
        if "viewOn" in database[collection_name].options():
            # we don't want to return views, as the command collstats can not be executed
            continue
        yield collection_name


def section_instance(server_status):
    sys.stdout.write("<<<mongodb_instance:sep(9)>>>\n")
    sys.stdout.write("version\t%s\n" % server_status.get("version", "n/a"))
    sys.stdout.write("pid\t%s\n" % server_status.get("pid", "n/a"))

    repl_info = server_status.get("repl")
    if not repl_info:
        sys.stdout.write("mode\tSingle Instance\n")

    elif repl_info.get("isWritablePrimary") or repl_info.get("ismaster"):
        sys.stdout.write("mode\tPrimary\n")

    elif repl_info.get("secondary"):
        sys.stdout.write("mode\tSecondary\n")

    else:
        sys.stdout.write("mode\tArbiter\n")

    if repl_info and repl_info.get("me"):
        sys.stdout.write("address\t%s\n" % repl_info.get("me", "n/a"))


def section_flushing(server_status):
    # key is depricated for MongoDB 4.0
    flushing_info = server_status.get("backgroundFlushing")
    if flushing_info is None:
        return
    sys.stdout.write("<<<mongodb_flushing>>>\n")
    sys.stdout.write("average_ms %s\n" % flushing_info.get("average_ms", "n/a"))
    sys.stdout.write("last_ms %s\n" % flushing_info.get("last_ms", "n/a"))
    sys.stdout.write("flushed %s\n" % flushing_info.get("flushes", "n/a"))


def _write_section_replica(
    primary,
    secondary_actives=None,
    secondary_passives=None,
    arbiters=None,
):
    """
    >>> _write_section_replica(None)
    <<<mongodb_replica:sep(0)>>>
    {"primary": null, "secondaries": {"active": [], "passive": []}, "arbiters": []}
    >>> _write_section_replica("primary")
    <<<mongodb_replica:sep(0)>>>
    {"primary": "primary", "secondaries": {"active": [], "passive": []}, "arbiters": []}
    >>> _write_section_replica("primary", secondary_actives=["1", "2"], secondary_passives=["3"], arbiters=["4"])
    <<<mongodb_replica:sep(0)>>>
    {"primary": "primary", "secondaries": {"active": ["1", "2"], "passive": ["3"]}, "arbiters": ["4"]}
    """
    sys.stdout.write("<<<mongodb_replica:sep(0)>>>\n")
    sys.stdout.write(
        json.dumps(
            {
                "primary": primary,
                "secondaries": {
                    "active": secondary_actives or [],
                    "passive": secondary_passives or [],
                },
                "arbiters": arbiters or [],
            }
        )
        + "\n"
    )


def sections_replica(server_status):
    """
    >>> sections_replica({})
    >>> sections_replica({"repl": {}})
    >>> sections_replica({"repl": {"primary": "abc"}})
    <<<mongodb_replica:sep(0)>>>
    {"primary": "abc", "secondaries": {"active": [], "passive": []}, "arbiters": []}
    """
    repl_info = server_status.get("repl")
    if not repl_info:
        return
    _write_section_replica(
        repl_info.get("primary"),
        secondary_actives=repl_info.get("hosts"),
        secondary_passives=repl_info.get("passives"),
        arbiters=repl_info.get("arbiters"),
    )


def sections_replica_set(client):
    try:
        rep_set_status = client.admin.command("replSetGetStatus")
    except pymongo.errors.OperationFailure:
        LOGGER.debug(
            "Calling replSetGetStatus returned an error. "
            "This might be ok if you have not configured replication on you mongodb server.",
            exc_info=True,
        )
        return

    sys.stdout.write("<<<mongodb_replica_set:sep(9)>>>\n")
    sys.stdout.write(
        "%s\n"
        % json.dumps(
            json.loads(dumps(rep_set_status)),
            separators=(",", ":"),
        ),
    )


def sections_replication_info(client, databases):
    """

    :param client:
    :param databases:
    :return:
    """
    if "oplog.rs" not in databases.get("local", {}).get("collections", {}):
        # replication not detected
        return

    sys.stdout.write("<<<mongodb_replication_info:sep(9)>>>\n")
    result_dict = _get_replication_info(client, databases)
    sys.stdout.write("%s\n" % json.dumps(result_dict, separators=(",", ":")))


def _get_replication_info(client, databases):
    """

    :param client: mongdb client
    :return: result
    """
    oplog = databases.get("local", {}).get("collstats", {}).get("oplog.rs", {})
    result = {}

    # Returns the total size of the oplog in bytes
    # This refers to the total amount of space allocated to the oplog rather than
    # the current size of operations stored in the oplog.
    if "maxSize" in oplog:
        result["logSizeBytes"] = oplog.get("maxSize")
    else:
        return result

    # Returns the total amount of space used by the oplog in bytes.
    # This refers to the total amount of space currently used by operations stored in the oplog rather than
    # the total amount of space allocated.
    result["usedBytes"] = oplog.get("size", 0)

    # Returns a timestamp for the first and last (i.e. earliest/latest) operation in the oplog.
    # Compare this value to the last write operation issued against the server.
    # Timestamp is time in seconds since epoch UTC
    firstc = client.local.oplog.rs.find_one(sort=[("$natural", 1)])
    lastc = client.local.oplog.rs.find_one(sort=[("$natural", -1)])
    if firstc and lastc:
        timestamp_first_operation = firstc.get("ts", None)
        timestamp_last_operation = lastc.get("ts", None)
        if timestamp_first_operation and timestamp_last_operation:
            result["tFirst"] = timestamp_first_operation.time
            result["tLast"] = timestamp_last_operation.time

    result["now"] = int(time.time())
    return result


def section_cluster(client, databases):
    """
    on router (mongos) node
    1. get all databases
    2. for each database, get all collections
    3. get stats for each collection
    5. get shards
    6. get chunks and count chunks and jumbo chunks per shard
    7. aggregate all into one conclusive dictionary
    :param client: mongodb client
    :param databases: database and collections statistic data as dictionary
    """
    # check if we run on mongos (router) node
    master_dict = client.admin.command("isMaster")
    if (
        not (master_dict.get("isWritablePrimary") or master_dict.get("ismaster"))
        or "msg" not in master_dict
        or master_dict.get("msg") != "isdbgrid"
    ):
        return

    sys.stdout.write("<<<mongodb_cluster:sep(0)>>>\n")

    # get balancer information
    balancer_dict = _get_balancer_info(client)

    # get cluster information for databases
    databases_cluster_info = client.config.databases.find({}, {"primary": 1, "partitioned": 1})
    _add_cluster_info(databases, databases_cluster_info)

    # get chunksize
    chunk_size_info = _get_chunk_size_information(client)

    # get additional collection information
    collections_dict = _get_collections_information(client)

    # get all shards
    shards_dict = _get_shards_information(client)

    # get number of chunks per shard
    chunks_dict = _count_chunks_per_shard(client, databases)

    # aggregate all information in one dict
    all_informations_dict = _aggregate_chunks_and_shards_info(
        databases, chunks_dict, shards_dict, collections_dict, balancer_dict, chunk_size_info
    )

    sys.stdout.write("%s\n" % json.dumps(all_informations_dict, separators=(",", ":")))


def _get_balancer_info(client):
    """
    get information if balancer is enabled for cluster
    get balancer statistics
    :param client: mongdb client
    :return: balancer status dictionary
    """
    balancer_dict = {}

    # check if balancer is enabled for cluster
    settings = client["config"]["settings"]
    settings_dict = settings.find_one({"_id": "balancer"})
    if settings_dict:
        balancer_dict["balancer_enabled"] = not settings_dict.get("stopped")
    else:
        balancer_dict["balancer_enabled"] = True

    # get balancer status
    status = client.admin.command("balancerStatus")
    _remove_keys(status, ["$clusterTime", "operationTime", "ok"])
    balancer_dict.update(status)

    return balancer_dict


def _add_cluster_info(databases, databases_cluster_info):
    """
    add additional information for databases to main databases dictionary
    :param databases: main database information dictionary
    :param databases_cluster_info: additional information per database
    """
    for database in databases_cluster_info:
        database_name = database.get("_id")
        database.pop("_id", None)
        if database_name in databases:
            databases.get(database_name).update(database)
        else:
            # add missing databases
            databases[database_name] = database
            databases.get(database_name).setdefault("collstats", {})
            databases.get(database_name).setdefault("collections", [])


def _aggregate_chunks_and_shards_info(
    databases_dict, chunks_dict, shards_dict, collections_dict, balancer_dict, settings_dict
):
    """
    generate one dictionary containing shards and chunks information per collection per database
    :param databases_dict: dictionary with database and collections statistic details
    :param chunks_dict: dictionary with number of chunks and jumps per shard
    :param shards_dict: dictionary with information which shard is on which host
    :return: dictionary with database, collections, shards and chunks information
    """
    # remove system databases
    _remove_keys(databases_dict, ["admin", "config"])

    # chunks_dict: add info 'number_of_chunks' from chunks dict to collections statistic dictionary
    for database_name in databases_dict:
        for collection_name in databases_dict.get(database_name).get("collections", []):
            collection_info = collections_dict.get(database_name, {}).get(collection_name, {})
            if collection_info:
                databases_dict.get(database_name).get("collstats").get(collection_name).update(
                    collection_info
                )
            for shard_name in shards_dict:
                chunks_info = (
                    chunks_dict.get(database_name, {}).get(collection_name, {}).get(shard_name, {})
                )
                if chunks_info and shard_name in databases_dict.get(database_name).get(
                    "collstats"
                ).get(collection_name).get("shards"):
                    databases_dict.get(database_name).get("collstats").get(collection_name).get(
                        "shards"
                    ).get(shard_name).update(chunks_info)

    # remove irrelevant data
    _lensing_data(databases_dict)

    # shards_dict: add shard information to collections statistic dictionary
    all_information_dict = {}
    all_information_dict["databases"] = databases_dict
    all_information_dict["shards"] = shards_dict
    all_information_dict["balancer"] = balancer_dict
    all_information_dict["settings"] = settings_dict

    return all_information_dict


def _lensing_data(databases):
    """
    removing data not needed for further processing
    removing data that is not json conform (mongoDB extended json format)
    :param databases: dictionary with databases, collections, shards information
    :return: json convertible dictionary
    """
    # clean up database data
    for database_name in databases:
        database = databases.get(database_name)
        _remove_keys(database, ["stats"])

        # clean up collections data
        for collection_name in database.get("collstats", {}):
            collection = database.get("collstats").get(collection_name)
            # remove irrelevant data
            _remove_keys(
                collection,
                [
                    "indexDetails",
                    "wiredTiger",
                    "operationTime",
                    "lastCommittedOpTime",
                    "$gleStats",
                    "$configServerState",
                    "$clusterTime",
                    "indexSizes",
                ],
            )

            # clean up shards data
            for shard_name in collection.get("shards", {}):
                shard = collection.get("shards").get(shard_name)
                # remove irrelevant data
                _remove_keys(
                    shard,
                    [
                        "indexDetails",
                        "wiredTiger",
                        "operationTime",
                        "lastCommittedOpTime",
                        "$gleStats",
                        "$configServerState",
                        "$clusterTime",
                        "indexSizes",
                    ],
                )


def _get_chunk_size_information(client):
    """
    chunk size default is 64MB. If the chunk size is changed, the changed value is in config.settings with id "chunksize".
    example:
    { "_id" : "chunksize", "value" : 64 }
    value is in MB
    :param client:
    :return:
    """
    chunk_size = 64 * 1024 * 1024
    for setting in client.config.settings.find({"_id": "chunksize"}):
        if "value" in setting:
            chunk_size = int(setting.get("value")) * 1024 * 1024
    return {"chunkSize": chunk_size}


def _get_collections_information(client):
    """
    get all documents from config collections
    :param client: mongodb client
    :return: dictionary with collections information
    """
    collections_def_dict = lambda: defaultdict(collections_def_dict)  # type: Callable
    collections_dict = collections_def_dict()
    for collection in client.config.collections.find(
        {}, set(["_id", "unique", "dropped", "noBalance"])
    ):
        database_name, collection_name = _split_namespace(collection.get("_id"))
        collection.pop("_id", None)
        collections_dict[database_name][collection_name] = collection
    return collections_dict


def _get_shards_information(client):
    """
    get all documents from shards collection
    :param client: mongodb client
    :return: dictionary with shards information
    """
    shard_dict = {}
    for shard in client.config.shards.find():
        shard_name = shard.get("_id")
        shard.pop("_id", None)
        shard_dict[shard_name] = shard
    return shard_dict


def _count_chunks_per_shard(client, databases):
    """
    count all chunks and jumbo chunks per shards
    :param client: mongodb client
    :return: dictionary with shards and sum of chunks and jumbo chunks
    """
    chunks_def_dict = lambda: defaultdict(chunks_def_dict)  # type: Callable
    chunks_dict = chunks_def_dict()

    # initialize dictionary
    # set default defaults for numberOfChunks and numberOfJumbos
    for database_name in databases:
        for collection_name in databases.get(database_name).get("collections", {}):
            for shard_name in (
                databases.get(database_name)
                .get("collstats")
                .get(collection_name, {})
                .get("shards", {})
            ):
                is_sharded = (
                    databases.get(database_name)
                    .get("collstats")
                    .get(collection_name, {})
                    .get("sharded", False)
                )
                if is_sharded:  # we count chunks below
                    chunks_dict[database_name][collection_name][shard_name]["numberOfChunks"] = 0
                else:  # unsharded => only 1 shard => nchunks = numberOfChunks (total number of chunks)
                    chunks_dict[database_name][collection_name][shard_name]["numberOfChunks"] = (
                        databases.get(database_name)
                        .get("collstats")
                        .get(collection_name)
                        .get("nchunks", 0)
                    )
                chunks_dict[database_name][collection_name][shard_name]["numberOfJumbos"] = 0

    chunks = client.config.chunks
    chunks_list = chunks.find({}, set(["ns", "shard", "jumbo"]))
    database_set = set()
    for chunk in chunks_list:

        # get database, collection and shard names
        shard_name = chunk.get("shard", None)
        database_name, collection_name = _split_namespace(chunk.get("ns"))

        # if there are no chunk information for this database, continue
        if database_name not in chunks_dict:
            continue

        # for later user
        database_set.add(database_name)

        # count number of chunks per shard
        if chunks_dict:
            chunks_dict.get(database_name).get(collection_name).get(shard_name)[
                "numberOfChunks"
            ] += 1

        # count number of jumbo chunks per shard
        if "jumbo" in chunk:
            chunks_dict.get(database_name).get(collection_name).get(shard_name)[
                "numberOfJumbos"
            ] += 1

    return chunks_dict


def _remove_keys(dictionary, list_of_keys):
    """
    remove keys from dictionary
    :param stats_dict:
    :param list_of_keys:
    :return:
    """
    for key_to_delete in list_of_keys:
        dictionary.pop(key_to_delete, None)


def _split_namespace(namespace):
    """
    split namespace into database name and collection name
    :param namespace:
    :return:
    """
    try:
        names = namespace.split(".", 1)
        if len(names) > 1:
            return names[0], names[1]
    except ValueError:
        pass
    except AttributeError:
        pass
    raise ValueError("error parsing namespace %s" % namespace)


def section_locks(server_status):
    sys.stdout.write("<<<mongodb_locks>>>\n")
    global_lock_info = server_status.get("globalLock")
    if global_lock_info:
        for what in ["activeClients", "currentQueue"]:
            if what in global_lock_info:
                for key, value in global_lock_info[what].items():
                    sys.stdout.write("%s %s %s\n" % (what, key, value))


def section_by_keys(section_name, keys, server_status, output_key=False):
    sys.stdout.write("<<<mongodb_%s>>>\n" % section_name)
    for key in keys:
        fmt = ("%s " % key if output_key else "") + "%s %s\n"
        for item in server_status.get(key, {}).items():
            sys.stdout.write(fmt % item)


def section_collections(client, databases):
    sys.stdout.write("<<<mongodb_collections:sep(9)>>>\n")
    database_collection = databases.copy()
    indexes_dict = _get_indexes_information(client, databases)

    for database_name in database_collection:
        database = database_collection.get(database_name)

        # remove stats section
        _remove_keys(database, ["stats"])

        # clean up collections data
        for collection_name in database.get("collstats", {}):
            collection = database.get("collstats").get(collection_name)
            # remove irrelevant data
            _remove_keys(
                collection,
                [
                    "indexDetails",
                    "wiredTiger",
                    "operationTime",
                    "lastCommittedOpTime",
                    "$gleStats",
                    "$configServerState",
                    "$clusterTime",
                    "shards",
                ],
            )
            if indexes_dict is None:
                continue
            collection["indexStats"] = (
                indexes_dict.get(database_name, {})
                .get(collection_name, {})
                .get(
                    "indexStats",
                    {},
                )
            )

    sys.stdout.write(
        "%s\n"
        % json.dumps(
            json.loads(dumps(database_collection)),
            separators=(",", ":"),
        ),
    )
    database_collection.clear()


def _get_indexes_information(client, databases):
    """
    get all documents from shards collection
    :param client: mongodb client
    :return: dictionary with shards information
    """
    indexes_def_dict = lambda: defaultdict(indexes_def_dict)  # type: Callable
    indexes_dict = indexes_def_dict()
    for database_name in databases:
        database = databases.get(database_name)
        for collection_name in database.get("collections", []):
            try:
                # $indexStat only available since mongodb v. 3.2
                indexes_dict[database_name][collection_name]["indexStats"] = client[database_name][
                    collection_name
                ].aggregate(
                    [
                        {
                            "$indexStats": {},
                        }
                    ]
                )
            except pymongo.errors.OperationFailure:
                LOGGER.debug("Could not access $indexStat", exc_info=True)
                return

    return indexes_dict


def get_timestamp(text):
    """parse timestamps like 'Nov  6 13:44:09.345' or '2015-10-17T05:35:24.234'"""
    text = text.split(".")[0]
    for pattern in ["%a %b %d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]:
        try:
            return time.mktime(time.strptime(text, pattern))
        except ValueError:
            pass


def read_statefile(state_file):
    try:
        with open(state_file) as state_fd:
            last_timestamp = int(state_fd.read())
    except (IOError, ValueError):
        return None, True

    if time.localtime(last_timestamp).tm_year >= 2015:
        return last_timestamp, False

    # Note: there is no year information in these loglines
    # As workaround we look at the creation date (year) of the last statefile
    # If it differs and there are new messages we start from the beginning
    statefile_year = time.localtime(os.stat(state_file).st_ctime).tm_year
    output_all = time.localtime().tm_year != statefile_year
    return last_timestamp, output_all


def update_statefile(state_file, startup_warnings):
    lines = startup_warnings.get("log")
    if not lines:
        return
    timestamp = get_timestamp(lines[-1])
    try:
        with open(state_file, "w") as state_fd:
            state_fd.write("%d" % timestamp)
    except (IOError, TypeError):
        # TypeError: timestamp was None, but at least ctime is updated.
        pass


def section_logwatch(client):
    if not MK_VARDIR:
        return

    sys.stdout.write("<<<logwatch>>>\n")
    sys.stdout.write("[[[MongoDB startupWarnings]]]\n")
    startup_warnings = client.admin.command({"getLog": "startupWarnings"})

    state_file = "%s/mongodb.state" % MK_VARDIR

    last_timestamp, output_all = read_statefile(state_file)

    for line in startup_warnings["log"]:
        state = "C"
        state_index = line.find("]") + 2
        if len(line) == state_index or line[state_index:].startswith("**  "):
            state = "."

        if "** WARNING:" in line:
            state = "W"

        if output_all or get_timestamp(line) > last_timestamp:
            sys.stdout.write("%s %s\n" % (state, line))

    update_statefile(state_file, startup_warnings)


DEFAULT_CFG_FILE = os.path.join(os.getenv("MK_CONFDIR", ""), "mk_mongodb.cfg")

LOGGER = logging.getLogger(__name__)


def parse_arguments(argv):

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--debug", action="store_true", help="""Debug mode: raise Python exceptions"""
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="""Verbose mode (for even more output use -vvv)""",
    )
    parser.add_argument(
        "-c",
        "--config-file",
        default=DEFAULT_CFG_FILE,
        help="""Read config file (default: %(default)s)""",
    )

    return parser.parse_args(argv)


def setup_logging(verbosity):
    fmt = "%%(levelname)5s: %s%%(message)s"
    if verbosity == 0:
        logging.basicConfig(level=logging.WARNING, format=fmt % "")
    elif verbosity == 1:
        logging.basicConfig(level=logging.INFO, format=fmt % "")
    else:
        logging.basicConfig(level=logging.DEBUG, format=fmt % "(line %(lineno)3d) ")


class MongoDBConfigParser(configparser.ConfigParser):
    """
    Python2/Python3 compatibility layer for ConfigParser
    """

    mongo_section = "MONGODB"

    def read_from_filename(self, filename):
        LOGGER.debug("trying to read %r", filename)
        if not os.path.exists(filename):
            LOGGER.warning("config file %s does not exist!", filename)
        else:
            with open(filename, "r") as cfg:
                if PY2:
                    self.readfp(cfg)  # pylint: disable=deprecated-method
                else:
                    self.read_file(cfg)
            LOGGER.info("read configuration file %r", filename)

    def get_mongodb_bool(self, option, *, default=None):
        if not self.has_option(self.mongo_section, option):
            return default
        return self.getboolean(self.mongo_section, option)

    def get_mongodb_str(self, option, *, default=None):
        if not self.has_option(self.mongo_section, option):
            return default
        return self.get(self.mongo_section, option)

    def get_mongodb_int(self, option, *, default=None):
        if not self.has_option(self.mongo_section, option):
            return default
        return self.getint(self.mongo_section, option)


class Config:
    def __init__(self, config):
        self.tls_enable = config.get_mongodb_bool("tls_enable")
        self.tls_verify = config.get_mongodb_bool("tls_verify")
        self.tls_ca_file = config.get_mongodb_str("tls_ca_file")

        self.auth_mechanism = config.get_mongodb_str("auth_mechanism")
        self.auth_source = config.get_mongodb_str("auth_source")

        self.host = config.get_mongodb_str("host")
        self.port = config.get_mongodb_int("port")
        self.username = config.get_mongodb_str("username")
        self.password = config.get_mongodb_str("password")

    def get_pymongo_config(self):
        # type:() -> Dict[str, Union[str, bool]]
        """
        return config for latest pymongo (3.12.X)
        """
        pymongo_config = {}
        if self.username:
            pymongo_config["username"] = self.username
            if self.password:
                pymongo_config["password"] = self.password

        if self.tls_enable is not None:
            pymongo_config["tls"] = self.tls_enable
            if self.tls_enable:
                if self.tls_verify is not None:
                    pymongo_config["tlsInsecure"] = not self.tls_verify
                if self.tls_ca_file is not None:
                    pymongo_config["tlsCAFile"] = self.tls_ca_file

        if self.auth_mechanism is not None:
            pymongo_config["authMechanism"] = self.auth_mechanism
        if self.auth_source is not None:
            pymongo_config["authSource"] = self.auth_source
        if self.host is not None:
            pymongo_config["host"] = self.host
        if self.port is not None:
            pymongo_config["port"] = self.port

        return pymongo_config


class PyMongoConfigTransformer:
    def __init__(self, config):
        # type:(Config) -> None
        self._config = config

    def transform(self, pymongo_config):
        version_transforms = [
            # apply the transform if the version of pymongo is lower than the
            # tuple defined here. For the oldest pymongo version, multiple
            # transforms will be executed.
            ((3, 9, 0), self._transform_tls_to_ssl),
            ((3, 5, 0), self._transform_credentials_to_uri),
        ]

        for version, transform_function in version_transforms:
            if PYMONGO_VERSION < version:
                pymongo_config = transform_function(pymongo_config)
        return pymongo_config

    def _transform_tls_to_ssl(self, pymongo_config):
        # type:(Dict[str, Union[str, bool]]) -> Dict[str, Union[str, bool]]
        if pymongo_config.get("tlsInsecure") is True:
            sys.stdout.write("<<<mongodb_instance:sep(9)>>>\n")
            sys.stdout.write(
                (
                    "error\tCan not use option 'tls_verify = False' with this pymongo version %s."
                    "This option is only available with pymongo > 3.9.0\n"
                )
                % str(PYMONGO_VERSION)
            )
            sys.exit(3)
        pymongo_config.pop("tlsInsecure", None)

        new_to_old = (
            ("tls", "ssl"),
            ("tlsCAFile", "ssl_ca_certs"),
        )
        for new_arg, old_arg in new_to_old:
            if new_arg in pymongo_config:
                pymongo_config[old_arg] = pymongo_config.pop(new_arg)
        return pymongo_config

    def _transform_credentials_to_uri(self, pymongo_config):
        # type:(Dict[str, Union[str, bool]]) -> Dict[str, Union[str, bool]]
        username = pymongo_config.pop("username", None)
        password = pymongo_config.pop("password", None)
        host = pymongo_config.pop("host", "localhost")
        port = pymongo_config.pop("port", 27017)
        if username is not None:
            password_element = ""
            if password is not None:
                password_element = ":{}".format(quote_plus(self._config.password))
            uri = "mongodb://{}{}@{}:{}".format(
                quote_plus(self._config.username), password_element, host, port
            )
        else:
            uri = "mongodb://{}:{}".format(host, port)
        pymongo_config["host"] = uri
        return pymongo_config


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    args = parse_arguments(argv)
    setup_logging(args.verbose)
    LOGGER.debug("parsed args: %r", args)
    if LOGGER.isEnabledFor(logging.INFO):
        LOGGER.info("python version: %s", sys.version.replace("\n", " "))
        LOGGER.info("pymongo version: %s", PYMONGO_VERSION)
        LOGGER.info("mk_mongodb version: %s", __version__)

    config_parser = MongoDBConfigParser()
    config_parser.read_from_filename(os.path.abspath(args.config_file))
    config = Config(config_parser)
    pymongo_config = PyMongoConfigTransformer(config).transform(config.get_pymongo_config())

    if LOGGER.isEnabledFor(logging.INFO):
        LOGGER.info("pymongo configuration:")
        message = str(pymongo_config)
        if config.password is not None:
            message = message.replace(config.password, "****")
            message = message.replace(quote_plus(config.password), "****")
        LOGGER.info(message)

    client = pymongo.MongoClient(read_preference=pymongo.ReadPreference.SECONDARY, **pymongo_config)
    try:
        # connecting is lazy, it might fail only now
        server_status = client.admin.command("serverStatus")
    except (pymongo.errors.OperationFailure, pymongo.errors.ConnectionFailure) as e:
        sys.stdout.write("<<<mongodb_instance:sep(9)>>>\n")
        sys.stdout.write("error\tFailed to connect\n")
        # TLS issues are thrown as pymongo.errors.ServerSelectionTimeoutError
        # (e.g. config with enabled TLS, but mongodb is plaintext only)
        # Give the user some hints what the issue could be:
        sys.stdout.write("details\t%s\n" % str(e))
        sys.exit(2)

    section_instance(server_status)
    repl_info = server_status.get("repl")
    if repl_info and not (repl_info.get("isWritablePrimary") or repl_info.get("ismaster")):
        # this is a special case: replica set without master
        # this is detected here
        if "primary" in repl_info and not repl_info.get("primary"):
            _write_section_replica(None)
        return

    piggyhost = repl_info.get("setName") if repl_info else None
    if piggyhost:
        sys.stdout.write("<<<<%s>>>>\n" % piggyhost)
    try:
        potentially_piggybacked_sections(client, server_status)
    finally:
        if piggyhost:
            sys.stdout.write("<<<<>>>>\n")


def potentially_piggybacked_sections(client, server_status):
    sections_replica(server_status)
    sections_replica_set(client)
    section_by_keys("asserts", ("asserts",), server_status)
    section_by_keys("connections", ("connections",), server_status)
    databases = get_database_info(client)
    section_locks(server_status)
    section_flushing(server_status)
    section_by_keys("mem", ("mem", "extra_info"), server_status)
    section_by_keys("counters", ("opcounters", "opcountersRepl"), server_status, output_key=True)
    section_collections(client, databases)
    section_cluster(client, databases)
    sections_replication_info(client, databases)
    section_logwatch(client)


if __name__ == "__main__":
    sys.exit(main())
