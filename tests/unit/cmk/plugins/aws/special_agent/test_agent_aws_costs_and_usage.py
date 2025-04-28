#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from argparse import Namespace as Args

from cmk.plugins.aws.special_agent.agent_aws import AWSConfig, CostsAndUsage, NamingConvention

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


def test_agent_aws_costs_and_usage() -> None:
    region = "us-east-1"
    config = AWSConfig("hostname", Args(), ([], []), NamingConvention.ip_region_instance)

    # TODO: FakeECClient shoud actually subclass ECClient.
    ce = CostsAndUsage(FakeCEClient(), region, config)  # type: ignore[arg-type]
    ce_results = ce.run().results

    assert ce.name == "costs_and_usage"
    assert len(ce_results) == 1
    ce_result = ce_results[0]
    assert ce_result.piggyback_hostname == ""
