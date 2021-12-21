#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.special_agents.agent_aws import AWSConfig, CostsAndUsage

from .agent_aws_fake_clients import CEGetCostsAndUsageIB


class FakeCEClient:
    def get_cost_and_usage(self, TimePeriod, Granularity, Metrics, GroupBy):
        return {
            "NextPageToken": "string",
            "GroupDefinitions": [
                {"Type": "'DIMENSION' | 'TAG'", "Key": "string"},
            ],
            "ResultsByTime": CEGetCostsAndUsageIB.create_instances(amount=1),
        }


def test_agent_aws_costs_and_usage():
    region = "us-east-1"
    config = AWSConfig("hostname", [], (None, None))

    ce = CostsAndUsage(FakeCEClient(), region, config)
    ce_results = ce.run().results

    assert ce.name == "costs_and_usage"
    assert len(ce_results) == 1
    ce_result = ce_results[0]
    assert ce_result.piggyback_hostname == ""
