# encoding: utf-8

import pytest

from cmk.special_agents.agent_aws import (
    AWSConfig,
    CostsAndUsage,
)

#TODO what about enums?

#   .--fake client---------------------------------------------------------.
#   |             __       _               _ _            _                |
#   |            / _| __ _| | _____    ___| (_) ___ _ __ | |_              |
#   |           | |_ / _` | |/ / _ \  / __| | |/ _ \ '_ \| __|             |
#   |           |  _| (_| |   <  __/ | (__| | |  __/ | | | |_              |
#   |           |_|  \__,_|_|\_\___|  \___|_|_|\___|_| |_|\__|             |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class FakeCEClient(object):
    def get_cost_and_usage(self, TimePeriod, Granularity, Metrics, GroupBy):
        return {
            'NextPageToken': 'string',
            'GroupDefinitions': [{
                'Type': "'DIMENSION' | 'TAG'",
                'Key': 'string'
            },],
            'ResultsByTime': [{
                'TimePeriod': {
                    'Start': 'string',
                    'End': 'string'
                },
                'Total': {
                    'string': {
                        'Amount': 'string',
                        'Unit': 'string'
                    }
                },
                'Groups': [{
                    'Keys': ['string',],
                    'Metrics': {
                        'string': {
                            'Amount': 'string',
                            'Unit': 'string'
                        }
                    }
                },],
                'Estimated': "True | False",
            },]
        }


#.


def test_agent_aws_costs_and_usage():
    region = 'us-east-1'
    config = AWSConfig('hostname', (None, None))

    ce = CostsAndUsage(FakeCEClient(), region, config)
    ce_results = ce.run().results

    #--CE-------------------------------------------------------------------
    assert ce.interval == 86400
    assert ce.name == "costs_and_usage"
    assert len(ce_results) == 1
    ce_result = ce_results[0]
    assert ce_result.piggyback_hostname == ''
