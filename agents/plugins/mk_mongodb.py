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
"""

__version__ = "2.0.0p23"

import os
import sys
import time
import inspect
import json
from collections import defaultdict

try:
    from typing import Callable, Dict, Any
except ImportError:
    pass

try:
    import pymongo  # type: ignore[import] # pylint: disable=import-error
except ImportError:
    sys.stdout.write("<<<mongodb_instance:sep(9)>>>\n")
    sys.stdout.write(
        "error\tpymongo library is not installed. Please install it on the monitored system (for Python 3 use: 'pip3 install pymongo', for Python 2 use 'pip install pymongo')\n"
    )
    sys.exit(1)

from bson.json_util import dumps  # type: ignore[import]

MK_VARDIR = os.environ.get("MK_VARDIR")


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
        databases[name]["collections"] = database.collection_names()
        databases[name]["stats"] = database.command("dbstats")
        databases[name]["collstats"] = {}
        for collection in databases[name]["collections"]:
            databases[name]["collstats"][collection] = database.command("collstats", collection)
    return databases


def section_instance(server_status):
    sys.stdout.write("<<<mongodb_instance:sep(9)>>>\n")
    sys.stdout.write("version\t%s\n" % server_status.get("version", "n/a"))
    sys.stdout.write("pid\t%s\n" % server_status.get("pid", "n/a"))

    repl_info = server_status.get("repl")
    if not repl_info:
        sys.stdout.write("mode\tSingle Instance\n")
        return

    if repl_info.get("ismaster"):
        sys.stdout.write("mode\tPrimary\n")
        return

    if repl_info.get("secondary"):
        sys.stdout.write("mode\tSecondary\n")
        return

    sys.stdout.write("mode\tArbiter\n")
    if repl_info.get("me"):
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
        json.dumps({
            "primary": primary,
            "secondaries": {
                "active": secondary_actives or [],
                "passive": secondary_passives or [],
            },
            "arbiters": arbiters or [],
        }) + "\n")


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
    except pymongo.errors.OperationFailure as e:
        sys.stderr.write("%s\n" % e)
        return

    sys.stdout.write("<<<mongodb_replica_set:sep(9)>>>\n")
    sys.stdout.write("%s\n" % json.dumps(
        json.loads(dumps(rep_set_status)),
        separators=(',', ':'),
    ),)


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
    sys.stdout.write("%s\n" % json.dumps(result_dict, separators=(',', ':')))


def _get_replication_info(client, databases):
    """

    :param client: mongdb client
    :return: result
    """
    oplog = databases.get("local", {}).get("collstats", {}).get("oplog.rs", {})
    result = dict()

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
    firstc = client.local.oplog.rs.find().sort('{$natural: 1}').limit(1)
    lastc = client.local.oplog.rs.find().sort('{$natural: -1}').limit(1)
    if firstc and lastc:
        timestamp_first_operation = firstc.next().get("ts", None)
        timestamp_last_operation = lastc.next().get("ts", None)
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
    if not master_dict.get(
            "ismaster") or "msg" not in master_dict or master_dict.get("msg") != "isdbgrid":
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
    all_informations_dict = _aggregate_chunks_and_shards_info(databases, chunks_dict, shards_dict,
                                                              collections_dict, balancer_dict,
                                                              chunk_size_info)

    sys.stdout.write("%s\n" % json.dumps(all_informations_dict, separators=(',', ':')))


def _get_balancer_info(client):
    """
    get information if balancer is enabled for cluster
    get balancer statistics
    :param client: mongdb client
    :return: balancer status dictionary
    """
    balancer_dict = dict()

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


def _aggregate_chunks_and_shards_info(databases_dict, chunks_dict, shards_dict, collections_dict,
                                      balancer_dict, settings_dict):
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
                    collection_info)
            for shard_name in shards_dict:
                chunks_info = chunks_dict.get(database_name, {}).get(collection_name,
                                                                     {}).get(shard_name, {})
                if chunks_info and shard_name in databases_dict.get(database_name).get(
                        "collstats").get(collection_name).get("shards"):
                    databases_dict.get(database_name).get("collstats").get(collection_name).get(
                        "shards").get(shard_name).update(chunks_info)

    # remove irrelevant data
    _lensing_data(databases_dict)

    # shards_dict: add shard information to collections statistic dictionary
    all_information_dict = dict()
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
            _remove_keys(collection, [
                "indexDetails", "wiredTiger", "operationTime", "lastCommittedOpTime", "$gleStats",
                "$configServerState", "$clusterTime", "indexSizes"
            ])

            # clean up shards data
            for shard_name in collection.get("shards", {}):
                shard = collection.get("shards").get(shard_name)
                # remove irrelevant data
                _remove_keys(shard, [
                    "indexDetails", "wiredTiger", "operationTime", "lastCommittedOpTime",
                    "$gleStats", "$configServerState", "$clusterTime", "indexSizes"
                ])


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
    for collection in client.config.collections.find({},
                                                     set(["_id", "unique", "dropped",
                                                          "noBalance"])):
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
    shard_dict = dict()
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
            for shard_name in databases.get(database_name).get("collstats").get(
                    collection_name, {}).get("shards", {}):
                is_sharded = databases.get(database_name).get("collstats").get(collection_name,
                                                                               {}).get(
                                                                                   "sharded", False)
                if is_sharded:  # we count chunks below
                    chunks_dict[database_name][collection_name][shard_name]["numberOfChunks"] = 0
                else:  # unsharded => only 1 shard => nchunks = numberOfChunks (total number of chunks)
                    chunks_dict[database_name][collection_name][shard_name][
                        "numberOfChunks"] = databases.get(database_name).get("collstats").get(
                            collection_name).get("nchunks", 0)
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
            chunks_dict.get(database_name).get(collection_name).get(
                shard_name)["numberOfChunks"] += 1

        # count number of jumbo chunks per shard
        if "jumbo" in chunk:
            chunks_dict.get(database_name).get(collection_name).get(
                shard_name)["numberOfJumbos"] += 1

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
            _remove_keys(collection, [
                "indexDetails", "wiredTiger", "operationTime", "lastCommittedOpTime", "$gleStats",
                "$configServerState", "$clusterTime", "shards"
            ])
            if indexes_dict is None:
                continue
            collection["indexStats"] = indexes_dict.get(database_name, {}).get(collection_name,
                                                                               {}).get(
                                                                                   "indexStats",
                                                                                   {},
                                                                               )

    sys.stdout.write(
        "%s\n" % json.dumps(
            json.loads(dumps(database_collection)),
            separators=(',', ':'),
        ),)
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
                    collection_name].aggregate([{
                        "$indexStats": {},
                    }])
            except pymongo.errors.OperationFailure as e:
                sys.stderr.write("%s\n" % e)
                return

    return indexes_dict


def get_timestamp(text):
    """parse timestamps like 'Nov  6 13:44:09.345' or '2015-10-17T05:35:24.234'"""
    text = text.split('.')[0]
    for pattern in ["%a %b %d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]:
        try:
            return time.mktime(time.strptime(text, pattern))
        except ValueError:
            pass


def read_statefile(state_file):
    try:
        state_fd = open(state_file)
        try:
            last_timestamp = int(state_fd.read())
        finally:
            state_fd.close()
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
        state_fd = open(state_file, 'w')
        try:
            state_fd.write("%d" % timestamp)
        finally:
            state_fd.close()
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


def main():
    client = pymongo.MongoClient(read_preference=pymongo.ReadPreference.SECONDARY)
    try:
        # connecting is lazy, it might fail only now
        server_status = client.admin.command("serverStatus")
    except pymongo.errors.ConnectionFailure:
        sys.stdout.write("<<<mongodb_instance:sep(9)>>>\n")
        sys.stdout.write("error\tInstance is down\n")
        return

    section_instance(server_status)
    repl_info = server_status.get("repl")
    if repl_info and not repl_info.get("ismaster"):
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
