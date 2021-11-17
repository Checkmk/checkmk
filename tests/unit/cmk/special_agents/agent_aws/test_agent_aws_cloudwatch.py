#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

from typing import List, Optional, Tuple

import pytest

from cmk.special_agents.agent_aws import (
    AWSConfig,
    CloudwatchAlarms,
    CloudwatchAlarmsLimits,
    ResultDistributor,
)

from .agent_aws_fake_clients import FakeCloudwatchClient


@pytest.fixture()
def get_cloudwatch_alarms_sections():
    def _create_cloudwatch_alarms_sections(alarm_names):
        region = "region"
        config = AWSConfig("hostname", [], (None, None))
        config.add_single_service_config("cloudwatch_alarms", alarm_names)

        fake_cloudwatch_client = FakeCloudwatchClient()

        cloudwatch_alarms_limits_distributor = ResultDistributor()

        cloudwatch_alarms_limits = CloudwatchAlarmsLimits(
            fake_cloudwatch_client, region, config, cloudwatch_alarms_limits_distributor
        )
        cloudwatch_alarms = CloudwatchAlarms(fake_cloudwatch_client, region, config)

        cloudwatch_alarms_limits_distributor.add(cloudwatch_alarms)
        return cloudwatch_alarms_limits, cloudwatch_alarms

    return _create_cloudwatch_alarms_sections


cloudwatch_params: List[Tuple[Optional[List[str]], int]] = [
    (None, 2),
    ([], 2),
    (["AlarmName-0"], 1),
    (["not found"], 1),
    (["AlarmName-0", "too many"], 1),
    (["AlarmName-0", "AlarmName-1"], 2),
    (["AlarmName-0", "AlarmName-1", "too many"], 2),
]


@pytest.mark.parametrize("alarm_names,amount_alarms", cloudwatch_params)
def test_agent_aws_cloudwatch_alarms_limits(
    get_cloudwatch_alarms_sections, alarm_names, amount_alarms
):
    cloudwatch_alarms_limits, _cloudwatch_alarms = get_cloudwatch_alarms_sections(alarm_names)
    cloudwatch_alarms_limits_results = cloudwatch_alarms_limits.run().results

    assert cloudwatch_alarms_limits.cache_interval == 300
    assert cloudwatch_alarms_limits.period == 600
    assert cloudwatch_alarms_limits.name == "cloudwatch_alarms_limits"

    assert len(cloudwatch_alarms_limits_results) == 1
    cloudwatch_alarms_limits_result = cloudwatch_alarms_limits_results[0]
    assert cloudwatch_alarms_limits_result.piggyback_hostname == ""

    assert len(cloudwatch_alarms_limits_result.content) == 1
    cloudwatch_alarms_limits_content = cloudwatch_alarms_limits_result.content[0]
    assert cloudwatch_alarms_limits_content.key == "cloudwatch_alarms"
    assert cloudwatch_alarms_limits_content.title == "CloudWatch Alarms"
    assert cloudwatch_alarms_limits_content.limit == 5000
    assert cloudwatch_alarms_limits_content.amount == 2


@pytest.mark.parametrize("alarm_names,amount_alarms", cloudwatch_params)
def test_agent_aws_cloudwatch_alarms(get_cloudwatch_alarms_sections, alarm_names, amount_alarms):
    cloudwatch_alarms_limits, cloudwatch_alarms = get_cloudwatch_alarms_sections(alarm_names)
    _cloudwatch_alarms_limits_results = cloudwatch_alarms_limits.run().results  # noqa: F841
    cloudwatch_alarms_results = cloudwatch_alarms.run().results

    assert cloudwatch_alarms.cache_interval == 300
    assert cloudwatch_alarms.period == 600
    assert cloudwatch_alarms.name == "cloudwatch_alarms"

    assert len(cloudwatch_alarms_results) == 1
    cloudwatch_alarms_result = cloudwatch_alarms_results[0]
    assert cloudwatch_alarms_result.piggyback_hostname == ""
    assert len(cloudwatch_alarms_result.content) == amount_alarms


@pytest.mark.parametrize("alarm_names,amount_alarms", cloudwatch_params)
def test_agent_aws_cloudwatch_alarms_without_limits(
    get_cloudwatch_alarms_sections, alarm_names, amount_alarms
):
    _cloudwatch_alarms_limits, cloudwatch_alarms = get_cloudwatch_alarms_sections(alarm_names)
    cloudwatch_alarms_results = cloudwatch_alarms.run().results

    assert cloudwatch_alarms.cache_interval == 300
    assert cloudwatch_alarms.period == 600
    assert cloudwatch_alarms.name == "cloudwatch_alarms"

    assert len(cloudwatch_alarms_results) == 1
    cloudwatch_alarms_result = cloudwatch_alarms_results[0]
    assert cloudwatch_alarms_result.piggyback_hostname == ""
    assert len(cloudwatch_alarms_result.content) == amount_alarms
