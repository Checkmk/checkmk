#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access,redefined-outer-name

import os
import sys

import pytest

if sys.version_info[0] == 2:
    import agents.plugins.mk_mongodb_2 as mk_mongodb  # pylint: disable=syntax-error
else:
    import agents.plugins.mk_mongodb as mk_mongodb


def read_dataset(filename):
    """
    reads pre-recorded mongodb server output ('serverStatus') from dataset directory.
    the dataset is in extended JSON format. (https://docs.mongodb.com/manual/reference/mongodb-extended-json/).
    :param filename: filename of the dataset
    :return: dataset as extended JSON
    """
    from bson.json_util import loads  # type: ignore[import]

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


def test_arbiter_instance_mongodb_4_0():
    """
    test mongodb cluster output:
    arbiter instance
    arbiter does not have a copy of data set and cannot become a primary,
    but it can vote for the primary.
    """
    dataset = read_dataset("mongo_output_arbiter-4.0.10.json")
    call_mk_mongodb_functions(dataset)
    mk_mongodb.sections_replica(dataset)


def test_arbiter_instance_mongodb_3_6():
    """
    test mongodb cluster output:
    arbiter instance
    arbiter does not have a copy of data set and cannot become a primary,
    but it can vote for the primary.
    """
    dataset = read_dataset("mongo_output_arbiter-3.6.13.json")
    call_mk_mongodb_functions(dataset)
    mk_mongodb.sections_replica(dataset)


def test_arbiter_instance_mongodb_3_4():
    """
    test mongodb cluster output:
    arbiter instance
    arbiter does not have a copy of data set and cannot become a primary,
    but it can vote for the primary.
    """
    dataset = read_dataset("mongo_output_arbiter-3.4.21.json")
    call_mk_mongodb_functions(dataset)
    mk_mongodb.sections_replica(dataset)


def test_config_instance_mongodb_4_0():
    """
    test mongodb cluster output:
    config instance
    config servers store the metadata for a sharded cluster.
    """
    dataset = read_dataset("mongo_output_config-4.0.10.json")
    call_mk_mongodb_functions(dataset)
    mk_mongodb.sections_replica(dataset)


def test_config_instance_mongodb_3_6():
    """
    test mongodb cluster output:
    config instance
    config servers store the metadata for a sharded cluster.
    """
    dataset = read_dataset("mongo_output_config-3.6.13.json")
    call_mk_mongodb_functions(dataset)
    mk_mongodb.sections_replica(dataset)


def test_config_instance_mongodb_3_4():
    """
    test mongodb cluster output:
    config instance
    config servers store the metadata for a sharded cluster.
    """
    dataset = read_dataset("mongo_output_config-3.4.21.json")
    call_mk_mongodb_functions(dataset)
    mk_mongodb.sections_replica(dataset)


def test_shard_instance_mongodb_4_0():
    """
    test mongodb cluster output:
    shard instance
    shard stores some portion of a sharded cluster’s total data set.
    """
    dataset = read_dataset("mongo_output_shard-4.0.10.json")
    call_mk_mongodb_functions(dataset)
    mk_mongodb.sections_replica(dataset)


def test_shard_instance_mongodb_3_6():
    """
    test mongodb cluster output:
    shard instance
    shard stores some portion of a sharded cluster’s total data set.
    """
    dataset = read_dataset("mongo_output_shard-3.6.13.json")
    call_mk_mongodb_functions(dataset)
    mk_mongodb.sections_replica(dataset)


def test_shard_instance_mongodb_3_4():
    """
    test mongodb cluster output:
    shard instance
    shard stores some portion of a sharded cluster’s total data set.
    """
    dataset = read_dataset("mongo_output_shard-3.4.21.json")
    call_mk_mongodb_functions(dataset)
    mk_mongodb.sections_replica(dataset)


def test_router_instance_mongodb_4_0():
    """
    test mongodb cluster output:
    mongos (router)
    mongos is a routing and load balancing process that acts an interface between an application and
    a MongoDB sharded cluster.
    """
    dataset = read_dataset("mongo_output_router-4.0.10.json")
    call_mk_mongodb_functions(dataset)
    mk_mongodb.sections_replica(dataset)


def test_router_instance_mongodb_3_6():
    """
    test mongodb cluster output:
    mongos (router)
    mongos is a routing and load balancing process that acts an interface between an application and
    a MongoDB sharded cluster.
    """
    dataset = read_dataset("mongo_output_router-3.6.13.json")
    call_mk_mongodb_functions(dataset)
    mk_mongodb.sections_replica(dataset)


def test_router_instance_mongodb_3_4():
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
        ({}, {}),
        (
            {
                "username": "t_user",
                "password": "t_pwd",
            },
            {
                "username": "t_user",
                "password": "t_pwd",
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
            },
        ),
    ],
)
def test_read_config(config, expected_pymongo_config):
    """
    see if the config is corretly transformed to pymongo arguments
    """
    config_parser = mk_mongodb.MongoDBConfigParser()
    config_parser.add_section("MONGODB")
    for key, value in config.items():
        config_parser.set("MONGODB", key, value)
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
            },
        ),
        (
            (3, 2, 0),
            {
                "host": "mongodb://username:%2F%3F%21%2F@example.com:27017",
                "ssl": True,
            },
        ),
    ],
)
def test_transform_config(pymongo_version, pymongo_config):
    class DummyConfig(mk_mongodb.Config):  # type: ignore[name-defined]
        def __init__(self) -> None:  # pylint: disable=super-init-not-called
            self.tls_enable = True
            self.tls_verify = None
            self.tls_ca_file = None
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
