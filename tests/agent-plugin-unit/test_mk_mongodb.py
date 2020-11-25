#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access,redefined-outer-name

import os
import pytest  # type: ignore[import]
from utils import import_module


@pytest.fixture(scope="module")
def mk_mongodb():
    return import_module("mk_mongodb.py")


def read_dataset(filename):
    """
    reads pre-recorded mongodb server output ('serverStatus') from dataset directory.
    the dataset is in extended JSON format. (https://docs.mongodb.com/manual/reference/mongodb-extended-json/).
    :param filename: filename of the dataset
    :return: dataset as extended JSON
    """
    from bson.json_util import loads  # type: ignore[import]
    dataset_file = os.path.abspath(
        os.path.join(os.path.dirname(__file__), 'datasets', 'mk_mongodb', filename))
    with open(dataset_file) as f:
        return loads(f.read())


def call_mk_mongodb_functions(mk_mongodb, dataset):
    """
    calls 4 functions of the mk_mongodb agent.
    :param mk_mongodb: reference to mk_mongodb agent
    :param dataset: dataset as extended JSON
    :return:
    """
    mk_mongodb.section_instance(dataset)
    mk_mongodb.section_locks(dataset)
    mk_mongodb.section_flushing(dataset)
    with pytest.raises(AttributeError):
        # AttributeError is thrown because mongodb client is None. Can be ignored here.
        mk_mongodb.potentially_piggybacked_sections(None, dataset)


def test_arbiter_instance_mongodb_4_0(mk_mongodb):
    """
    test mongodb cluster output:
    arbiter instance
    arbiter does not have a copy of data set and cannot become a primary,
    but it can vote for the primary.
    :param mk_mongodb: reference to mk_mongodb agent
    """
    dataset = read_dataset("mongo_output_arbiter-4.0.10.json")
    call_mk_mongodb_functions(mk_mongodb, dataset)
    mk_mongodb.sections_replica(dataset)


def test_arbiter_instance_mongodb_3_6(mk_mongodb):
    """
    test mongodb cluster output:
    arbiter instance
    arbiter does not have a copy of data set and cannot become a primary,
    but it can vote for the primary.
    :param mk_mongodb: reference to mk_mongodb agent
    """
    dataset = read_dataset("mongo_output_arbiter-3.6.13.json")
    call_mk_mongodb_functions(mk_mongodb, dataset)
    mk_mongodb.sections_replica(dataset)


def test_arbiter_instance_mongodb_3_4(mk_mongodb):
    """
    test mongodb cluster output:
    arbiter instance
    arbiter does not have a copy of data set and cannot become a primary,
    but it can vote for the primary.
    :param mk_mongodb: reference to mk_mongodb agent
    """
    dataset = read_dataset("mongo_output_arbiter-3.4.21.json")
    call_mk_mongodb_functions(mk_mongodb, dataset)
    mk_mongodb.sections_replica(dataset)


def test_config_instance_mongodb_4_0(mk_mongodb):
    """
    test mongodb cluster output:
    config instance
    config servers store the metadata for a sharded cluster.
    :param mk_mongodb: reference to mk_mongodb agent
    """
    dataset = read_dataset("mongo_output_config-4.0.10.json")
    call_mk_mongodb_functions(mk_mongodb, dataset)
    mk_mongodb.sections_replica(dataset)


def test_config_instance_mongodb_3_6(mk_mongodb):
    """
    test mongodb cluster output:
    config instance
    config servers store the metadata for a sharded cluster.
    :param mk_mongodb: reference to mk_mongodb agent
    """
    dataset = read_dataset("mongo_output_config-3.6.13.json")
    call_mk_mongodb_functions(mk_mongodb, dataset)
    mk_mongodb.sections_replica(dataset)


def test_config_instance_mongodb_3_4(mk_mongodb):
    """
    test mongodb cluster output:
    config instance
    config servers store the metadata for a sharded cluster.
    :param mk_mongodb: reference to mk_mongodb agent
    """
    dataset = read_dataset("mongo_output_config-3.4.21.json")
    call_mk_mongodb_functions(mk_mongodb, dataset)
    mk_mongodb.sections_replica(dataset)


def test_shard_instance_mongodb_4_0(mk_mongodb):
    """
    test mongodb cluster output:
    shard instance
    shard stores some portion of a sharded cluster’s total data set.
    :param mk_mongodb: reference to mk_mongodb agent
    """
    dataset = read_dataset("mongo_output_shard-4.0.10.json")
    call_mk_mongodb_functions(mk_mongodb, dataset)
    mk_mongodb.sections_replica(dataset)


def test_shard_instance_mongodb_3_6(mk_mongodb):
    """
    test mongodb cluster output:
    shard instance
    shard stores some portion of a sharded cluster’s total data set.
    :param mk_mongodb: reference to mk_mongodb agent
    """
    dataset = read_dataset("mongo_output_shard-3.6.13.json")
    call_mk_mongodb_functions(mk_mongodb, dataset)
    mk_mongodb.sections_replica(dataset)


def test_shard_instance_mongodb_3_4(mk_mongodb):
    """
    test mongodb cluster output:
    shard instance
    shard stores some portion of a sharded cluster’s total data set.
    :param mk_mongodb: reference to mk_mongodb agent
    """
    dataset = read_dataset("mongo_output_shard-3.4.21.json")
    call_mk_mongodb_functions(mk_mongodb, dataset)
    mk_mongodb.sections_replica(dataset)


def test_router_instance_mongodb_4_0(mk_mongodb):
    """
    test mongodb cluster output:
    mongos (router)
    mongos is a routing and load balancing process that acts an interface between an application and
    a MongoDB sharded cluster.
    :param mk_mongodb: reference to mk_mongodb agent
    """
    dataset = read_dataset("mongo_output_router-4.0.10.json")
    call_mk_mongodb_functions(mk_mongodb, dataset)
    mk_mongodb.sections_replica(dataset)


def test_router_instance_mongodb_3_6(mk_mongodb):
    """
    test mongodb cluster output:
    mongos (router)
    mongos is a routing and load balancing process that acts an interface between an application and
    a MongoDB sharded cluster.
    :param mk_mongodb: reference to mk_mongodb agent
    """
    dataset = read_dataset("mongo_output_router-3.6.13.json")
    call_mk_mongodb_functions(mk_mongodb, dataset)
    mk_mongodb.sections_replica(dataset)


def test_router_instance_mongodb_3_4(mk_mongodb):
    """
    test mongodb cluster output:
    mongos (router)
    mongos is a routing and load balancing process that acts an interface between an application and
    a MongoDB sharded cluster.
    :param mk_mongodb: reference to mk_mongodb agent
    """
    dataset = read_dataset("mongo_output_router-3.4.21.json")
    call_mk_mongodb_functions(mk_mongodb, dataset)
    mk_mongodb.sections_replica(dataset)
