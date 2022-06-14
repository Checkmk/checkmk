#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

import pytest

from cmk.special_agents.agent_aws import AWSConfig, RDS, RDSLimits, RDSSummary, ResultDistributor

from .agent_aws_fake_clients import (
    FakeCloudwatchClient,
    RDSDescribeAccountAttributesIB,
    RDSDescribeDBInstancesIB,
    RDSListTagsForResourceIB,
)


class DBInstanceNotFoundFault(Exception):
    pass


class Exceptions:
    def __init__(self) -> None:
        self.DBInstanceNotFoundFault = DBInstanceNotFoundFault


class Paginator:
    def paginate(self, DBInstanceIdentifier=None):
        db_instances = RDSDescribeDBInstancesIB.create_instances(amount=3)
        if DBInstanceIdentifier is not None:
            db_instances = [
                instance
                for instance in db_instances
                if instance["DBInstanceIdentifier"] == DBInstanceIdentifier
            ]
        yield {
            "Marker": "string",
            "DBInstances": db_instances,
        }


class FakeRDSClient:
    def __init__(self) -> None:
        self.exceptions = Exceptions()

    def describe_account_attributes(self):
        return {
            "AccountQuotas": RDSDescribeAccountAttributesIB.create_instances(amount=1)[0][
                "AccountQuotas"
            ],
        }

    def list_tags_for_resource(self, ResourceName=None):
        if ResourceName == "DBInstanceArn-2":  # the third table has no tags
            tags = []
        else:
            tags = RDSListTagsForResourceIB.create_instances(amount=1)
        return {"TagList": tags}

    def get_paginator(self, operation_name):
        if operation_name == "describe_db_instances":
            return Paginator()
        raise NotImplementedError


@pytest.fixture()
def get_rds_sections():
    def _create_rds_sections(names, tags):
        region = "region"
        config = AWSConfig("hostname", [], (None, None))
        config.add_single_service_config("rds_names", names)
        config.add_service_tags("rds_tags", tags)

        fake_rds_client = FakeRDSClient()
        fake_cloudwatch_client = FakeCloudwatchClient()

        rds_summary_distributor = ResultDistributor()

        rds_limits = RDSLimits(FakeRDSClient(), region, config)
        rds_summary = RDSSummary(fake_rds_client, region, config, rds_summary_distributor)
        rds = RDS(fake_cloudwatch_client, region, config)

        rds_summary_distributor.add(rds)
        return rds_limits, rds_summary, rds

    return _create_rds_sections


rds_params = [
    (
        None,
        (None, None),
        ["DBInstanceIdentifier-0", "DBInstanceIdentifier-1", "DBInstanceIdentifier-2"],
    ),
    (
        None,
        ([["FOO"]], [["BAR"]]),
        [],
    ),
    (
        None,
        ([["Key-0"]], [["Value-0"]]),
        ["DBInstanceIdentifier-0", "DBInstanceIdentifier-1"],
    ),
    (
        None,
        ([["Key-0", "Foo"]], [["Value-0", "Bar"]]),
        ["DBInstanceIdentifier-0", "DBInstanceIdentifier-1"],
    ),
    (
        ["DBInstanceIdentifier-0"],
        (None, None),
        ["DBInstanceIdentifier-0"],
    ),
    (
        ["DBInstanceIdentifier-0", "Foobar"],
        (None, None),
        ["DBInstanceIdentifier-0"],
    ),
    (
        ["DBInstanceIdentifier-0", "DBInstanceIdentifier-1"],
        (None, None),
        ["DBInstanceIdentifier-0", "DBInstanceIdentifier-1"],
    ),
    (
        ["DBInstanceIdentifier-0", "DBInstanceIdentifier-2"],
        ([["FOO"]], [["BAR"]]),
        ["DBInstanceIdentifier-0", "DBInstanceIdentifier-2"],
    ),
]


@pytest.mark.parametrize("names,tags,found_instances", rds_params)
def test_agent_aws_rds_limits(get_rds_sections, names, tags, found_instances) -> None:
    rds_limits, _rds_summary, _rds = get_rds_sections(names, tags)
    rds_limits_results = rds_limits.run().results

    assert rds_limits.cache_interval == 300
    assert rds_limits.period == 600
    assert rds_limits.name == "rds_limits"

    assert len(rds_limits_results) == 1

    rds_limits_result = rds_limits_results[0]
    assert rds_limits_result.piggyback_hostname == ""
    assert len(rds_limits_result.content) == 15


@pytest.mark.parametrize("names,tags,found_instances", rds_params)
def test_agent_aws_rds_summary(get_rds_sections, names, tags, found_instances) -> None:
    _rds_limits, rds_summary, _rds = get_rds_sections(names, tags)
    rds_summary_results = rds_summary.run().results

    assert rds_summary.cache_interval == 300
    assert rds_summary.period == 600
    assert rds_summary.name == "rds_summary"

    if found_instances:
        assert len(rds_summary_results) == 1
        rds_summary_result = rds_summary_results[0]
        assert rds_summary_result.piggyback_hostname == ""
        assert len(rds_summary_result.content) == len(found_instances)
    else:
        assert len(rds_summary_results) == 0


@pytest.mark.parametrize("names,tags,found_instances", rds_params)
def test_agent_aws_rds(get_rds_sections, names, tags, found_instances) -> None:
    _rds_limits, rds_summary, rds = get_rds_sections(names, tags)
    _rds_summary_results = rds_summary.run().results
    rds_results = rds.run().results

    assert rds.cache_interval == 300
    assert rds.period == 600
    assert rds.name == "rds"

    if found_instances:
        assert len(rds_results) == 1
        rds_result = rds_results[0]
        assert rds_result.piggyback_hostname == ""
        # 21 (metrics) * X (DBs) == Y (len results)
        assert len(rds_result.content) == 21 * len(found_instances)
    else:
        assert len(rds_results) == 0
