#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Agent plugins still need to support Python 3.4
# ruff: noqa: UP006  # PEP 585 (Type Hinting Generics In Standard Collections) is a Python 3.9 feature
# ruff: noqa: UP007  # PEP 604 (Allow writing union types as X | Y) is a Python 3.10 feature
# ruff: noqa: UP035  # PEP 585 (Type Hinting Generics In Standard Collections) is a Python 3.9 feature

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

import json
import os
from typing import Dict, Mapping, Tuple, Union

import pymongo
import pytest

from cmk.plugins.mongodb.agents import mk_mongodb


def read_dataset(filename):
    """
    reads pre-recorded mongodb server output ('serverStatus') from dataset directory.
    the dataset is in extended JSON format. (https://docs.mongodb.com/manual/reference/mongodb-extended-json/).
    :param filename: filename of the dataset
    :return: dataset as extended JSON
    """
    from bson.json_util import loads

    dataset_file = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "datasets", "mk_mongodb", filename)
    )
    with open(dataset_file) as f:
        return loads(f.read())


def call_mk_mongodb_functions(dataset):
    """
    calls 4 functions of the mk_mongodb agent.
    :param dataset: dataset as extended JSON
    :return:
    """
    mk_mongodb.section_instance(dataset)
    mk_mongodb.section_locks(dataset)
    mk_mongodb.section_flushing(dataset)
    with pytest.raises(AttributeError):
        # AttributeError is thrown because mongodb client is None. Can be ignored here.
        mk_mongodb.potentially_piggybacked_sections(None, dataset)


def test_arbiter_instance_mongodb_4_0() -> None:
    """
    test mongodb cluster output:
    arbiter instance
    arbiter does not have a copy of data set and cannot become a primary,
    but it can vote for the primary.
    """
    dataset = read_dataset("mongo_output_arbiter-4.0.10.json")
    call_mk_mongodb_functions(dataset)
    mk_mongodb.sections_replica(dataset)


def test_arbiter_instance_mongodb_3_6() -> None:
    """
    test mongodb cluster output:
    arbiter instance
    arbiter does not have a copy of data set and cannot become a primary,
    but it can vote for the primary.
    """
    dataset = read_dataset("mongo_output_arbiter-3.6.13.json")
    call_mk_mongodb_functions(dataset)
    mk_mongodb.sections_replica(dataset)


def test_arbiter_instance_mongodb_3_4() -> None:
    """
    test mongodb cluster output:
    arbiter instance
    arbiter does not have a copy of data set and cannot become a primary,
    but it can vote for the primary.
    """
    dataset = read_dataset("mongo_output_arbiter-3.4.21.json")
    call_mk_mongodb_functions(dataset)
    mk_mongodb.sections_replica(dataset)


def test_config_instance_mongodb_4_0() -> None:
    """
    test mongodb cluster output:
    config instance
    config servers store the metadata for a sharded cluster.
    """
    dataset = read_dataset("mongo_output_config-4.0.10.json")
    call_mk_mongodb_functions(dataset)
    mk_mongodb.sections_replica(dataset)


def test_config_instance_mongodb_3_6() -> None:
    """
    test mongodb cluster output:
    config instance
    config servers store the metadata for a sharded cluster.
    """
    dataset = read_dataset("mongo_output_config-3.6.13.json")
    call_mk_mongodb_functions(dataset)
    mk_mongodb.sections_replica(dataset)


def test_config_instance_mongodb_3_4() -> None:
    """
    test mongodb cluster output:
    config instance
    config servers store the metadata for a sharded cluster.
    """
    dataset = read_dataset("mongo_output_config-3.4.21.json")
    call_mk_mongodb_functions(dataset)
    mk_mongodb.sections_replica(dataset)


def test_shard_instance_mongodb_4_0() -> None:
    """
    test mongodb cluster output:
    shard instance
    shard stores some portion of a sharded cluster’s total data set.
    """
    dataset = read_dataset("mongo_output_shard-4.0.10.json")
    call_mk_mongodb_functions(dataset)
    mk_mongodb.sections_replica(dataset)


def test_shard_instance_mongodb_3_6() -> None:
    """
    test mongodb cluster output:
    shard instance
    shard stores some portion of a sharded cluster’s total data set.
    """
    dataset = read_dataset("mongo_output_shard-3.6.13.json")
    call_mk_mongodb_functions(dataset)
    mk_mongodb.sections_replica(dataset)


def test_shard_instance_mongodb_3_4() -> None:
    """
    test mongodb cluster output:
    shard instance
    shard stores some portion of a sharded cluster’s total data set.
    """
    dataset = read_dataset("mongo_output_shard-3.4.21.json")
    call_mk_mongodb_functions(dataset)
    mk_mongodb.sections_replica(dataset)


def test_router_instance_mongodb_4_0() -> None:
    """
    test mongodb cluster output:
    mongos (router)
    mongos is a routing and load balancing process that acts an interface between an application and
    a MongoDB sharded cluster.
    """
    dataset = read_dataset("mongo_output_router-4.0.10.json")
    call_mk_mongodb_functions(dataset)
    mk_mongodb.sections_replica(dataset)


def test_router_instance_mongodb_3_6() -> None:
    """
    test mongodb cluster output:
    mongos (router)
    mongos is a routing and load balancing process that acts an interface between an application and
    a MongoDB sharded cluster.
    """
    dataset = read_dataset("mongo_output_router-3.6.13.json")
    call_mk_mongodb_functions(dataset)
    mk_mongodb.sections_replica(dataset)


def test_router_instance_mongodb_3_4() -> None:
    """
    test mongodb cluster output:
    mongos (router)
    mongos is a routing and load balancing process that acts an interface between an application and
    a MongoDB sharded cluster.
    """
    dataset = read_dataset("mongo_output_router-3.4.21.json")
    call_mk_mongodb_functions(dataset)
    mk_mongodb.sections_replica(dataset)


@pytest.mark.parametrize(
    "config, expected_pymongo_config",
    [
        (
            {},
            {
                "read_preference": pymongo.ReadPreference.SECONDARY,
            },
        ),
        (
            {
                "username": "t_user",
                "password": "t_pwd",
            },
            {
                "username": "t_user",
                "password": "t_pwd",
                "read_preference": pymongo.ReadPreference.SECONDARY,
            },
        ),
        (
            {
                "username": "t_user",
                "password": "t_pwd",
                "tls_enable": "1",
            },
            {
                "username": "t_user",
                "password": "t_pwd",
                "tls": True,
                "read_preference": pymongo.ReadPreference.SECONDARY,
            },
        ),
        (
            {
                "username": "t_user",
                "password": "t_pwd",
                "tls_enable": "1",
                "tls_verify": "0",
                "tls_ca_file": "/path/to/ca.pem",
            },
            {
                "username": "t_user",
                "password": "t_pwd",
                "tls": True,
                "tlsInsecure": True,
                "tlsCAFile": "/path/to/ca.pem",
                "read_preference": pymongo.ReadPreference.SECONDARY,
            },
        ),
        (
            {
                "username": "t_user",
                "password": "t_pwd",
                "tls_enable": "1",
                "tls_verify": "0",
                "tls_ca_file": "/path/to/ca.pem",
                "auth_mechanism": "DEFAULT",
                "auth_source": "not_admin",
            },
            {
                "authMechanism": "DEFAULT",
                "authSource": "not_admin",
                "password": "t_pwd",
                "tls": True,
                "tlsCAFile": "/path/to/ca.pem",
                "tlsInsecure": True,
                "username": "t_user",
                "read_preference": pymongo.ReadPreference.SECONDARY,
            },
        ),
    ],
)
def test_read_config(
    config: Mapping[str, str], expected_pymongo_config: Dict[str, Union[str, bool]]
) -> None:
    """
    see if the config is corretly transformed to pymongo arguments
    """
    config_parser = mk_mongodb.MongoDBConfigParser()
    config_parser.add_section("MONGODB")
    for key, value in config.items():
        config_parser.set("MONGODB", key, value)

    if mk_mongodb.PYMONGO_VERSION >= (3, 11, 0):
        expected_pymongo_config.update({"directConnection": True})

    assert mk_mongodb.Config(config_parser).get_pymongo_config() == expected_pymongo_config


@pytest.mark.parametrize(
    "pymongo_version, pymongo_config",
    [
        (
            (999, 9, 9),
            {
                "host": "example.com",
                "password": "/?!/",
                "tls": True,
                "username": "username",
                "read_preference": pymongo.ReadPreference.SECONDARY,
                "directConnection": True,
            },
        ),
        (
            (3, 11, 0),
            {
                "host": "example.com",
                "password": "/?!/",
                "tls": True,
                "username": "username",
                "read_preference": pymongo.ReadPreference.SECONDARY,
                "directConnection": True,
            },
        ),
        (
            (3, 10, 0),
            {
                "host": "example.com",
                "password": "/?!/",
                "tls": True,
                "username": "username",
                "read_preference": pymongo.ReadPreference.SECONDARY,
            },
        ),
        (
            (3, 8, 0),
            {
                "host": "example.com",
                "password": "/?!/",
                "ssl": True,
                "username": "username",
                "read_preference": pymongo.ReadPreference.SECONDARY,
            },
        ),
        (
            (3, 4, 0),
            {
                "host": "mongodb://username:%2F%3F%21%2F@example.com:27017",
                "ssl": True,
                "read_preference": pymongo.ReadPreference.SECONDARY,
            },
        ),
    ],
)
def test_transform_config(
    pymongo_version: Tuple[int, int, int], pymongo_config: Mapping[str, Union[str, bool]]
) -> None:
    class DummyConfig(mk_mongodb.Config):
        def __init__(self) -> None:
            self.tls_enable = True
            self.tls_verify = None
            self.tls_ca_file = None
            self.tls_cert_key_file = None
            self.auth_mechanism = None
            self.auth_source = None
            self.port = None
            self.host = "example.com"
            self.password = "/?!/"
            self.username = "username"

    config = DummyConfig()

    original_pymongo_version = mk_mongodb.PYMONGO_VERSION
    try:
        mk_mongodb.PYMONGO_VERSION = pymongo_version
        result = mk_mongodb.PyMongoConfigTransformer(config).transform(config.get_pymongo_config())
    finally:
        mk_mongodb.PYMONGO_VERSION = original_pymongo_version

    assert result == pymongo_config


def _stdout_stderr(captured_output_and_error):
    if isinstance(captured_output_and_error, tuple):
        # Python 3.3 for some reason
        return captured_output_and_error
    return captured_output_and_error.out, captured_output_and_error.err


def test_sections_replica_empty_section(capsys):
    mk_mongodb.sections_replica({})
    captured_output_and_error = capsys.readouterr()
    stdout, stderr = _stdout_stderr(captured_output_and_error)

    assert not stdout
    assert not stderr


def test_sections_replica_no_replicas(capsys):
    mk_mongodb.sections_replica({"repl": {}})
    captured_output_and_error = capsys.readouterr()
    stdout, stderr = _stdout_stderr(captured_output_and_error)

    assert not stdout
    assert not stderr


def test_sections_replica_primary(capsys):
    mk_mongodb.sections_replica({"repl": {"primary": "abc"}})
    captured_output_and_error = capsys.readouterr()
    stdout, stderr = _stdout_stderr(captured_output_and_error)

    header, json_body, noop = stdout.split("\n")
    replicas = json.loads(json_body)

    assert header == "<<<mongodb_replica:sep(0)>>>"

    assert len(replicas) == 3
    assert replicas["primary"] == "abc"
    assert sorted(replicas["secondaries"].items()) == [("active", []), ("passive", [])]
    assert replicas["arbiters"] == []

    assert not noop
    assert not stderr


def test_sections_replica_active_secondaries(capsys):
    """Make sure primaries are removed from hosts when secondaries are determined."""

    mk_mongodb.sections_replica({"repl": {"primary": "abc", "hosts": ["abc", "def"]}})
    captured_output_and_error = capsys.readouterr()
    stdout, stderr = _stdout_stderr(captured_output_and_error)

    header, json_body, noop = stdout.split("\n")
    replicas = json.loads(json_body)

    assert header == "<<<mongodb_replica:sep(0)>>>"

    assert len(replicas) == 3
    assert replicas["primary"] == "abc"
    assert sorted(replicas["secondaries"].items()) == [("active", ["def"]), ("passive", [])]
    assert replicas["arbiters"] == []

    assert not noop
    assert not stderr


def test_sections_replica_passive_secondaries(capsys):
    mk_mongodb.sections_replica({"repl": {"primary": "abc", "passives": ["def"]}})
    captured_output_and_error = capsys.readouterr()
    stdout, stderr = _stdout_stderr(captured_output_and_error)

    header, json_body, noop = stdout.split("\n")
    replicas = json.loads(json_body)

    assert header == "<<<mongodb_replica:sep(0)>>>"

    assert len(replicas) == 3
    assert replicas["primary"] == "abc"
    assert sorted(replicas["secondaries"].items()) == [("active", []), ("passive", ["def"])]
    assert replicas["arbiters"] == []

    assert not noop
    assert not stderr


def test_sections_replica_arbiters(capsys):
    mk_mongodb.sections_replica({"repl": {"primary": "abc", "arbiters": ["def"]}})
    captured_output_and_error = capsys.readouterr()
    stdout, stderr = _stdout_stderr(captured_output_and_error)

    header, json_body, noop = stdout.split("\n")
    replicas = json.loads(json_body)

    assert header == "<<<mongodb_replica:sep(0)>>>"

    assert len(replicas) == 3
    assert replicas["primary"] == "abc"
    assert sorted(replicas["secondaries"].items()) == [("active", []), ("passive", [])]
    assert replicas["arbiters"] == ["def"]

    assert not noop
    assert not stderr


def test__write_section_replica_none_primary(capsys):
    mk_mongodb._write_section_replica(None)  # noqa: SLF001
    captured_output_and_error = capsys.readouterr()
    stdout, stderr = _stdout_stderr(captured_output_and_error)

    header, json_body, noop = stdout.split("\n")
    replicas = json.loads(json_body)

    assert header == "<<<mongodb_replica:sep(0)>>>"

    assert len(replicas) == 3
    assert replicas["primary"] is None
    assert sorted(replicas["secondaries"].items()) == [("active", []), ("passive", [])]
    assert replicas["arbiters"] == []

    assert not noop
    assert not stderr


class _FakeCursor:
    def __init__(self, documents):
        self._documents = list(documents)

    def sort(self, spec):
        return _FakeCursor(
            sorted(self._documents, key=lambda d: d["ts"].time, reverse=spec[0][1] < 0)
        )

    def limit(self, number):
        return _FakeCursor(self._documents[:number])

    def next(self):
        return self._documents[0]


class _FakeCollection:
    def __init__(self, options=None, index_stats=None, documents=()):
        self._options = options or {}
        self._index_stats = index_stats
        self._documents = documents

    def options(self):
        return self._options

    def aggregate(self, _pipeline):
        if self._index_stats is None:
            raise pymongo.errors.OperationFailure("$indexStats not supported")
        return self._index_stats

    def find(self):
        return _FakeCursor(self._documents)


class _FakeDatabase:
    def __init__(self, collections=None, commands=None):
        self._collections = collections or {}
        self._commands = commands or {}

    def __getitem__(self, name):
        return self._collections[name]

    def __getattr__(self, name):
        try:
            return self._collections[name]
        except KeyError:
            raise AttributeError(name) from None

    def list_collection_names(self):
        return list(self._collections)

    collection_names = list_collection_names

    def command(self, command, *args):
        result = self._commands[command if isinstance(command, str) else str(command)]
        if isinstance(result, Exception):
            raise result
        return result(*args) if callable(result) else result


class _FakeClient:
    def __init__(self, databases):
        self._databases = databases

    def __getitem__(self, name):
        return self._databases[name]

    def __getattr__(self, name):
        try:
            return self._databases[name]
        except KeyError:
            raise AttributeError(name) from None

    def list_database_names(self):
        return list(self._databases)


def test_server_status_without_global_lock_yields_empty_locks_section(capsys):
    mk_mongodb.section_locks({})

    assert capsys.readouterr().out == "<<<mongodb_locks>>>\n"


def test_section_by_keys_prefixes_lines_with_key_if_requested(capsys):
    mk_mongodb.section_by_keys(
        "mem",
        ("mem", "extra_info"),
        {"mem": {"resident": 80}, "extra_info": {"page_faults": 3}},
        output_key=True,
    )

    assert capsys.readouterr().out == (
        "<<<mongodb_mem>>>\nmem resident 80\nextra_info page_faults 3\n"
    )


def test_database_info_contains_stats_of_collections_but_not_views():
    client = _FakeClient(
        {
            "shop": _FakeDatabase(
                collections={
                    "orders": _FakeCollection(),
                    "orders_view": _FakeCollection(options={"viewOn": "orders"}),
                },
                commands={
                    "dbstats": {"objects": 3},
                    "collstats": lambda name: {"ns": "shop.%s" % name},
                },
            )
        }
    )

    assert mk_mongodb.get_database_info(client) == {
        "shop": {
            "collections": ["orders"],
            "stats": {"objects": 3},
            "collstats": {"orders": {"ns": "shop.orders"}},
        }
    }


def test_replica_set_status_is_written_as_json(capsys):
    client = _FakeClient(
        {"admin": _FakeDatabase(commands={"replSetGetStatus": {"set": "rs0", "myState": 1}})}
    )

    mk_mongodb.sections_replica_set(client)

    header, body = capsys.readouterr().out.splitlines()
    assert (header, json.loads(body)) == (
        "<<<mongodb_replica_set:sep(9)>>>",
        {"set": "rs0", "myState": 1},
    )


def test_replica_set_section_is_skipped_without_replication(capsys):
    client = _FakeClient(
        {
            "admin": _FakeDatabase(
                commands={"replSetGetStatus": pymongo.errors.OperationFailure("not running")}
            )
        }
    )

    mk_mongodb.sections_replica_set(client)

    assert not capsys.readouterr().out


def test_replication_info_is_skipped_without_oplog(capsys):
    mk_mongodb.sections_replication_info(_FakeClient({}), {"local": {"collections": []}})

    assert not capsys.readouterr().out


def test_replication_info_without_oplog_size_is_empty(capsys):
    databases = {"local": {"collections": ["oplog.rs"], "collstats": {"oplog.rs": {}}}}

    mk_mongodb.sections_replication_info(_FakeClient({}), databases)

    assert capsys.readouterr().out == "<<<mongodb_replication_info:sep(9)>>>\n{}\n"


def test_replication_info_reports_oplog_size_and_time_window(capsys):
    from bson.timestamp import Timestamp

    oplog = _FakeCollection(
        documents=[{"ts": Timestamp(1566895270, 1)}, {"ts": Timestamp(1566891670, 1)}]
    )
    client = _FakeClient(
        {"local": _FakeDatabase(collections={"oplog": _FakeDatabase(collections={"rs": oplog})})}
    )
    databases = {
        "local": {
            "collections": ["oplog.rs"],
            "collstats": {"oplog.rs": {"maxSize": 16830742272, "size": 9765922}},
        }
    }

    mk_mongodb.sections_replication_info(client, databases)

    info = json.loads(capsys.readouterr().out.splitlines()[1])
    info.pop("now")
    assert info == {
        "logSizeBytes": 16830742272,
        "usedBytes": 9765922,
        "tFirst": 1566891670,
        "tLast": 1566895270,
    }


def test_collections_section_drops_internal_stats_and_adds_index_stats(capsys):
    client = _FakeClient(
        {
            "shop": _FakeDatabase(
                collections={"orders": _FakeCollection(index_stats=[{"name": "_id_"}])}
            )
        }
    )
    databases = {
        "shop": {
            "collections": ["orders"],
            "stats": {"objects": 3},
            "collstats": {"orders": {"size": 100, "wiredTiger": {}, "shards": {}}},
        }
    }

    mk_mongodb.section_collections(client, databases)

    header, body = capsys.readouterr().out.splitlines()
    assert (header, json.loads(body)) == (
        "<<<mongodb_collections:sep(9)>>>",
        {
            "shop": {
                "collections": ["orders"],
                "collstats": {"orders": {"size": 100, "indexStats": [{"name": "_id_"}]}},
            }
        },
    )


def test_collections_section_omits_index_stats_if_unsupported(capsys):
    client = _FakeClient({"shop": _FakeDatabase(collections={"orders": _FakeCollection()})})
    databases = {"shop": {"collections": ["orders"], "collstats": {"orders": {"size": 100}}}}

    mk_mongodb.section_collections(client, databases)

    assert json.loads(capsys.readouterr().out.splitlines()[1]) == {
        "shop": {"collections": ["orders"], "collstats": {"orders": {"size": 100}}}
    }


def test_cluster_section_is_only_written_on_router(capsys):
    client = _FakeClient(
        {"admin": _FakeDatabase(commands={"isMaster": {"ismaster": True, "msg": "not-a-router"}})}
    )

    mk_mongodb.section_cluster(client, {})

    assert not capsys.readouterr().out


def test_iso_timestamps_ignore_fractions_of_seconds():
    assert (
        mk_mongodb.get_timestamp("2015-10-17T05:35:24.234")
        - mk_mongodb.get_timestamp("2015-10-17T05:35:20")
        == 4
    )


def test_unparsable_timestamp_is_none():
    assert mk_mongodb.get_timestamp("Nov  6 13:44:09.345") is None


def test_missing_statefile_requests_all_log_lines(tmp_path):
    assert mk_mongodb.read_statefile(str(tmp_path / "mongodb.state")) == (None, True)


def test_invalid_statefile_requests_all_log_lines(tmp_path):
    state_file = tmp_path / "mongodb.state"
    with open(str(state_file), "w") as state_fd:
        state_fd.write("garbage")

    assert mk_mongodb.read_statefile(str(state_file)) == (None, True)


def test_statefile_round_trip_keeps_last_log_timestamp(tmp_path):
    state_file = str(tmp_path / "mongodb.state")

    mk_mongodb.update_statefile(
        state_file, {"log": ["2015-10-17T05:35:20.000 first", "2015-10-17T05:35:24.234 last"]}
    )

    assert mk_mongodb.read_statefile(state_file) == (
        mk_mongodb.get_timestamp("2015-10-17T05:35:24"),
        False,
    )


def test_empty_startup_warnings_leave_statefile_untouched(tmp_path):
    state_file = tmp_path / "mongodb.state"

    mk_mongodb.update_statefile(str(state_file), {"log": []})

    assert not state_file.exists()
