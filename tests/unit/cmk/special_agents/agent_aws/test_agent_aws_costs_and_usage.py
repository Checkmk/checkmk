# encoding: utf-8

from agent_aws_fake_clients import (
    CEGetCostsAndUsageIB,)

from cmk.special_agents.agent_aws import (
    AWSConfig,
    CostsAndUsage,
)


class FakeCEClient(object):
    def get_cost_and_usage(self, TimePeriod, Granularity, Metrics, GroupBy):
        return {
            'NextPageToken': 'string',
            'GroupDefinitions': [{
                'Type': "'DIMENSION' | 'TAG'",
                'Key': 'string'
            },],
            'ResultsByTime': CEGetCostsAndUsageIB.create_instances(amount=1),
        }


def test_agent_aws_costs_and_usage():
    region = 'us-east-1'
    config = AWSConfig('hostname', (None, None))

    ce = CostsAndUsage(FakeCEClient(), region, config)
    ce_results = ce.run().results

    #--CE-------------------------------------------------------------------
    assert ce.cache_interval == 86400
    assert ce.name == "costs_and_usage"
    assert len(ce_results) == 1
    ce_result = ce_results[0]
    assert ce_result.piggyback_hostname == ''
