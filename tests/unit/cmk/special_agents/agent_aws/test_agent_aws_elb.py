# pylint: disable=redefined-outer-name

import pytest
from agent_aws_fake_clients import (
    FakeCloudwatchClient,
    ELBDescribeLoadBalancersIC,
    ELBDescribeTagsIC,
    ELBDescribeInstanceHealthIC,
)

from cmk.special_agents.agent_aws import (
    AWSConfig,
    ResultDistributor,
    ELBLimits,
    ELBSummaryGeneric,
    ELBLabelsGeneric,
    ELBHealth,
    ELB,
)


class FakeELBClient(object):
    def describe_load_balancers(self, LoadBalancerNames=None):
        return {
            'LoadBalancerDescriptions': ELBDescribeLoadBalancersIC.create_instances(amount=3),
            'NextMarker': 'string',
        }

    def describe_account_limits(self):
        return {
            'Limits': [
                {
                    'Name': 'classic-load-balancers',
                    'Max': 10,
                },
                {
                    'Name': 'classic-listeners',
                    'Max': 10,
                },
                {
                    'Name': 'classic-registered-instances',
                    'Max': 10,
                },
            ],
            'NextMarker': 'string'
        }

    def describe_tags(self, LoadBalancerNames=None):
        tag_descrs = []
        for lb_name in LoadBalancerNames:
            if lb_name not in ["LoadBalancerName-0", "LoadBalancerName-1"]:
                continue
            tag_descrs.extend(ELBDescribeTagsIC.create_instances(amount=1))
        return {'TagDescriptions': tag_descrs}

    def describe_instance_health(self, LoadBalancerName=None):
        return {'InstanceStates': ELBDescribeInstanceHealthIC.create_instances(amount=1)}


@pytest.fixture()
def get_elb_sections():
    def _create_elb_sections(tags):
        region = 'region'
        config = AWSConfig('hostname', (None, None))
        config.add_single_service_config('elb_names', None)
        config.add_service_tags('elb_tags', tags)

        fake_elb_client = FakeELBClient()
        fake_cloudwatch_client = FakeCloudwatchClient()

        elb_limits_distributor = ResultDistributor()
        elb_summary_distributor = ResultDistributor()

        elb_limits = ELBLimits(fake_elb_client, region, config, elb_limits_distributor)
        elb_summary = ELBSummaryGeneric(
            fake_elb_client, region, config, elb_summary_distributor, resource='elb')
        elb_labels = ELBLabelsGeneric(fake_elb_client, region, config, resource='elb')
        elb_health = ELBHealth(fake_elb_client, region, config)
        elb = ELB(fake_cloudwatch_client, region, config)

        elb_limits_distributor.add(elb_summary)
        elb_summary_distributor.add(elb_labels)
        elb_summary_distributor.add(elb_health)
        elb_summary_distributor.add(elb)
        return elb_limits, elb_summary, elb_labels, elb_health, elb

    return _create_elb_sections


elb_params = [
    ((None, None), ['LoadBalancerName-0', 'LoadBalancerName-1', 'LoadBalancerName-2'],
     ['LoadBalancerName-0', 'LoadBalancerName-1']),
    (([['FOO']], [['BAR']]), [], []),
    (([['Key-0']], [['Value-0']]), ['LoadBalancerName-0', 'LoadBalancerName-1'],
     ['LoadBalancerName-0', 'LoadBalancerName-1']),
    (([['Key-0', 'Foo']], [['Value-0', 'Bar']]), ['LoadBalancerName-0', 'LoadBalancerName-1'],
     ['LoadBalancerName-0', 'LoadBalancerName-1']),
]


@pytest.mark.parametrize("tags,found_instances,found_instances_with_labels", elb_params)
def test_agent_aws_elb_limits(get_elb_sections, tags, found_instances, found_instances_with_labels):
    elb_limits, _elb_summary, _elb_labels, _elb_health, _elb = get_elb_sections(tags)
    elb_limits_results = elb_limits.run().results

    assert elb_limits.interval == 300
    assert elb_limits.name == "elb_limits"
    assert len(elb_limits_results) == 4
    for result in elb_limits_results:
        if result.piggyback_hostname == '':
            assert len(result.content) == 1
        else:
            assert len(result.content) == 2


@pytest.mark.parametrize("tags,found_instances,found_instances_with_labels", elb_params)
def test_agent_aws_elb_summary(get_elb_sections, tags, found_instances,
                               found_instances_with_labels):
    elb_limits, elb_summary, _elb_labels, _elb_health, _elb = get_elb_sections(tags)
    _elb_limits_results = elb_limits.run().results
    elb_summary_results = elb_summary.run().results

    assert elb_summary.interval == 300
    assert elb_summary.name == "elb_summary"

    if found_instances:
        assert len(elb_summary_results) == 1
        elb_summary_result = elb_summary_results[0]
        assert elb_summary_result.piggyback_hostname == ''
        assert len(elb_summary_result.content) == len(found_instances)

    else:
        assert len(elb_summary_results) == 0


@pytest.mark.parametrize("tags,found_instances,found_instances_with_labels", elb_params)
def test_agent_aws_elb_labels(get_elb_sections, tags, found_instances, found_instances_with_labels):
    elb_limits, elb_summary, elb_labels, _elb_health, _elb = get_elb_sections(tags)
    _elb_limits_results = elb_limits.run().results
    _elb_summary_results = elb_summary.run().results
    elb_labels_results = elb_labels.run().results

    assert elb_labels.interval == 300
    assert elb_labels.name == "elb_generic_labels"
    assert len(elb_labels_results) == len(found_instances_with_labels)
    for result in elb_labels_results:
        assert result.piggyback_hostname != ''


@pytest.mark.parametrize("tags,found_instances,found_instances_with_labels", elb_params)
def test_agent_aws_elb_health(get_elb_sections, tags, found_instances, found_instances_with_labels):
    elb_limits, elb_summary, _elb_labels, elb_health, _elb = get_elb_sections(tags)
    _elb_limits_results = elb_limits.run().results
    _elb_summary_results = elb_summary.run().results
    elb_health_results = elb_health.run().results

    assert elb_health.interval == 300
    assert elb_health.name == "elb_health"
    assert len(elb_health_results) == len(found_instances)
    for result in elb_health_results:
        assert result.piggyback_hostname != ''


@pytest.mark.parametrize("tags,found_instances,found_instances_with_labels", elb_params)
def test_agent_aws_elb(get_elb_sections, tags, found_instances, found_instances_with_labels):
    elb_limits, elb_summary, _elb_labels, _elb_health, elb = get_elb_sections(tags)
    _elb_limits_results = elb_limits.run().results
    _elb_summary_results = elb_summary.run().results
    elb_results = elb.run().results

    assert elb.interval == 300
    assert elb.name == "elb"
    assert len(elb_results) == len(found_instances)
    for result in elb_results:
        assert result.piggyback_hostname != ''
        # 13 metrics
        assert len(result.content) == 13
