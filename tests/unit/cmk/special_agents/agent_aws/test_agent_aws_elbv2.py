# pylint: disable=redefined-outer-name

import pytest
from agent_aws_fake_clients import (
    ELBv2DescribeLoadBalancersIB,
    ELBv2DescribeTargetGroupsIB,
    ELBv2DescribeListenersIB,
    ELBv2DescribeRulesIB,
    ELBv2DescribeAccountLimitsIB,
    ELBv2DescribeTargetHealthIB,
)

from cmk.special_agents.agent_aws import (
    AWSConfig,
    ResultDistributor,
    ELBv2Limits,
    ELBSummaryGeneric,
    ELBv2TargetGroups,
)


class FakeELBv2Client(object):
    def describe_load_balancers(self):
        return {
            'LoadBalancers': ELBv2DescribeLoadBalancersIB.create_instances(amount=1),
            'NextMarker': 'string',
        }

    def describe_target_groups(self, LoadBalancerArn=None):
        return {
            'TargetGroups': ELBv2DescribeTargetGroupsIB.create_instances(amount=1),
            'NextMarker': 'string',
        }

    def describe_listeners(self, LoadBalancerArn=None):
        return {
            'Listeners': ELBv2DescribeListenersIB.create_instances(amount=1),
            'NextMarker': 'string',
        }

    def describe_rules(self, ListenerArn=None):
        return {
            'Rules': ELBv2DescribeRulesIB.create_instances(amount=1),
            'NextMarker': 'string',
        }

    def describe_account_limits(self):
        return {
            'Limits': ELBv2DescribeAccountLimitsIB.create_instances(amount=1)[0]['Limits'],
            'NextMarker': 'string',
        }

    def describe_target_health(self, TargetGroupArn=None):
        return {
            'TargetHealthDescriptions': ELBv2DescribeTargetHealthIB.create_instances(amount=1),
        }


@pytest.fixture()
def get_elbv2_sections():
    def _create_elbv2_sections(names, tags):
        region = 'region'
        config = AWSConfig('hostname', (None, None))
        config.add_single_service_config('elbv2_names', names)
        config.add_service_tags('elbv2_tags', tags)

        fake_elbv2_client = FakeELBv2Client()

        elbv2_limits_distributor = ResultDistributor()
        elbv2_summary_distributor = ResultDistributor()

        elbv2_limits = ELBv2Limits(fake_elbv2_client, region, config, elbv2_limits_distributor)
        elbv2_summary = ELBSummaryGeneric(
            fake_elbv2_client, region, config, elbv2_summary_distributor, resource='elbv2')
        elbv2_target_groups = ELBv2TargetGroups(fake_elbv2_client, region, config)

        elbv2_limits_distributor.add(elbv2_summary)
        elbv2_summary_distributor.add(elbv2_target_groups)
        return elbv2_limits, elbv2_summary, elbv2_target_groups

    return _create_elbv2_sections


def test_agent_aws_elbv2_limits(get_elbv2_sections):
    elbv2_limits, _elbv2_summary, _elbv2_target_groups = get_elbv2_sections(None, (None, None))
    _elbv2_limits_results = elbv2_limits.run().results

    assert elbv2_limits.cache_interval == 300
    assert elbv2_limits.name == "elbv2_limits"


def test_agent_aws_elbv2_summary(get_elbv2_sections):
    elbv2_limits, elbv2_summary, _elbv2_target_groups = get_elbv2_sections(None, (None, None))
    _elbv2_limits_results = elbv2_limits.run().results
    _elbv2_summary_results = elbv2_summary.run().results

    assert elbv2_summary.cache_interval == 300
    assert elbv2_summary.name == "elbv2_summary"


def test_agent_aws_elbv2_target_groups(get_elbv2_sections):
    elbv2_limits, elbv2_summary, elbv2_target_groups = get_elbv2_sections(None, (None, None))
    _elbv2_limits_results = elbv2_limits.run().results
    _elbv2_summary_results = elbv2_summary.run().results
    _elbv2_target_groups_results = elbv2_target_groups.run().results

    assert elbv2_target_groups.cache_interval == 300
    assert elbv2_target_groups.name == "elbv2_target_groups"
