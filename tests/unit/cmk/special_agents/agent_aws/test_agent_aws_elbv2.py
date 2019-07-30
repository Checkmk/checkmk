# pylint: disable=redefined-outer-name

import pytest
from agent_aws_fake_clients import (
    FakeCloudwatchClient,
    ELBv2DescribeLoadBalancersIB,
    ELBv2DescribeTargetGroupsIB,
    ELBv2DescribeListenersIB,
    ELBv2DescribeRulesIB,
    ELBv2DescribeAccountLimitsIB,
    ELBv2DescribeTargetHealthIB,
    ELBDescribeTagsIB,
)

from cmk.special_agents.agent_aws import (
    AWSConfig,
    ResultDistributor,
    ELBv2Limits,
    ELBSummaryGeneric,
    ELBLabelsGeneric,
    ELBv2TargetGroups,
    ELBv2Application,
    ELBv2Network,
)


class FakeELBv2Client(object):
    def describe_load_balancers(self):
        return {
            'LoadBalancers': ELBv2DescribeLoadBalancersIB.create_instances(amount=3),
            'NextMarker': 'string',
        }

    def describe_tags(self, ResourceArns=None):
        tag_descrs = []
        for lb_arn in ResourceArns:
            if lb_arn not in ["LoadBalancerArn-0", "LoadBalancerArn-1"]:
                continue
            tag_descrs.extend(ELBDescribeTagsIB.create_instances(amount=1))
        return {'TagDescriptions': tag_descrs}

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
        fake_cloudwatch_client = FakeCloudwatchClient()

        elbv2_limits_distributor = ResultDistributor()
        elbv2_summary_distributor = ResultDistributor()

        elbv2_limits = ELBv2Limits(fake_elbv2_client, region, config, elbv2_limits_distributor)
        elbv2_summary = ELBSummaryGeneric(fake_elbv2_client,
                                          region,
                                          config,
                                          elbv2_summary_distributor,
                                          resource='elbv2')
        elbv2_labels = ELBLabelsGeneric(fake_elbv2_client, region, config, resource='elbv2')
        elbv2_target_groups = ELBv2TargetGroups(fake_elbv2_client, region, config)
        elbv2_application = ELBv2Application(fake_cloudwatch_client, region, config)
        elbv2_network = ELBv2Network(fake_cloudwatch_client, region, config)

        elbv2_limits_distributor.add(elbv2_summary)
        elbv2_summary_distributor.add(elbv2_labels)
        elbv2_summary_distributor.add(elbv2_target_groups)
        elbv2_summary_distributor.add(elbv2_application)
        elbv2_summary_distributor.add(elbv2_network)
        return elbv2_limits, elbv2_summary, elbv2_labels, elbv2_target_groups, elbv2_application, elbv2_network

    return _create_elbv2_sections


elbv2_tags_params = [
    ((None, None), ['LoadBalancerName-0', 'LoadBalancerName-1',
                    'LoadBalancerName-2'], ['LoadBalancerName-0', 'LoadBalancerName-1']),
    (([['FOO']], [['BAR']]), [], []),
    (([['Key-0']], [['Value-0']]), ['LoadBalancerName-0', 'LoadBalancerName-1'],
     ['LoadBalancerName-0', 'LoadBalancerName-1']),
    (([['Key-0',
        'Foo']], [['Value-0',
                   'Bar']]), ['LoadBalancerName-0',
                              'LoadBalancerName-1'], ['LoadBalancerName-0', 'LoadBalancerName-1']),
]

elbv2_params = [
    (None, (None, None), ['LoadBalancerName-0', 'LoadBalancerName-1',
                          'LoadBalancerName-2'], ['LoadBalancerName-0', 'LoadBalancerName-1']),
    (None, ([['FOO']], [['BAR']]), [], []),
    (None, ([['Key-0']], [['Value-0']]), ['LoadBalancerName-0', 'LoadBalancerName-1'],
     ['LoadBalancerName-0', 'LoadBalancerName-1']),
    (None, ([['Key-0', 'Foo']], [['Value-0', 'Bar']]), ['LoadBalancerName-0', 'LoadBalancerName-1'],
     ['LoadBalancerName-0', 'LoadBalancerName-1']),
    (['LoadBalancerName-0'], (None, None), ['LoadBalancerName-0'], ['LoadBalancerName-0']),
    (['LoadBalancerName-0',
      'Foobar'], (None, None), ['LoadBalancerName-0'], ['LoadBalancerName-0']),
    (['LoadBalancerName-0', 'LoadBalancerName-1'], (None, None),
     ['LoadBalancerName-0', 'LoadBalancerName-1'], ['LoadBalancerName-0', 'LoadBalancerName-1']),
    (['LoadBalancerName-0',
      'LoadBalancerName-2'], (None, None), ['LoadBalancerName-0',
                                            'LoadBalancerName-2'], ['LoadBalancerName-0']),
]


@pytest.mark.parametrize("names,tags,found_instances,found_instances_with_labels", elbv2_params)
def test_agent_aws_elbv2_limits(get_elbv2_sections, names, tags, found_instances,
                                found_instances_with_labels):
    elbv2_limits, _elbv2_summary, _elbv2_labels, _elbv2_target_groups, _elbv2_application, _elbv2_network = get_elbv2_sections(
        names, tags)
    elbv2_limits_results = elbv2_limits.run().results

    assert elbv2_limits.cache_interval == 300
    assert elbv2_limits.name == "elbv2_limits"
    assert len(elbv2_limits_results) == 4
    for result in elbv2_limits_results:
        if result.piggyback_hostname == '':
            assert len(result.content) == 3
        else:
            # Dependent on load balancer type "application" or "network" we have 2 or 4 limits
            assert len(result.content) in (2, 4)


@pytest.mark.parametrize("names,tags,found_instances,found_instances_with_labels", elbv2_params)
def test_agent_aws_elbv2_summary(get_elbv2_sections, names, tags, found_instances,
                                 found_instances_with_labels):
    elbv2_limits, elbv2_summary, _elbv2_labels, _elbv2_target_groups, _elbv2_application, _elbv2_network = get_elbv2_sections(
        names, tags)
    _elbv2_limits_results = elbv2_limits.run().results
    elbv2_summary_results = elbv2_summary.run().results

    assert elbv2_summary.cache_interval == 300
    assert elbv2_summary.name == "elbv2_summary"

    if found_instances:
        assert len(elbv2_summary_results) == 1
        elbv2_summary_result = elbv2_summary_results[0]
        assert elbv2_summary_result.piggyback_hostname == ''
        assert len(elbv2_summary_result.content) == len(found_instances)

    else:
        assert len(elbv2_summary_results) == 0


@pytest.mark.parametrize("names,tags,found_instances,found_instances_with_labels", elbv2_params)
def test_agent_aws_elbv2_labels(get_elbv2_sections, names, tags, found_instances,
                                found_instances_with_labels):
    elbv2_limits, elbv2_summary, elbv2_labels, _elbv2_target_groups, _elbv2_health, _elbv2 = get_elbv2_sections(
        names, tags)
    _elbv2_limits_results = elbv2_limits.run().results
    _elbv2_summary_results = elbv2_summary.run().results
    elbv2_labels_results = elbv2_labels.run().results

    assert elbv2_labels.cache_interval == 300
    assert elbv2_labels.name == "elbv2_generic_labels"
    assert len(elbv2_labels_results) == len(found_instances_with_labels)
    for result in elbv2_labels_results:
        assert result.piggyback_hostname != ''


@pytest.mark.parametrize("names,tags,found_instances,found_instances_with_labels", elbv2_params)
def test_agent_aws_elbv2_target_groups(get_elbv2_sections, names, tags, found_instances,
                                       found_instances_with_labels):
    elbv2_limits, elbv2_summary, _elbv2_labels, elbv2_target_groups, _elbv2_application, _elbv2_network = get_elbv2_sections(
        names, tags)
    _elbv2_limits_results = elbv2_limits.run().results
    _elbv2_summary_results = elbv2_summary.run().results
    elbv2_target_groups_results = elbv2_target_groups.run().results

    assert elbv2_target_groups.cache_interval == 300
    assert elbv2_target_groups.name == "elbv2_target_groups"
    assert len(elbv2_target_groups_results) == len(found_instances)
    for result in elbv2_target_groups_results:
        assert result.piggyback_hostname != ''


@pytest.mark.parametrize("names,tags,found_instances,found_instances_with_labels", elbv2_params)
def test_agent_aws_elbv2_application(get_elbv2_sections, names, tags, found_instances,
                                     found_instances_with_labels):
    elbv2_limits, elbv2_summary, _elbv2_labels, _elbv2_target_groups, elbv2_application, _elbv2_network = get_elbv2_sections(
        names, tags)
    _elbv2_limits_results = elbv2_limits.run().results
    _elbv2_summary_results = elbv2_summary.run().results
    elbv2_application_results = elbv2_application.run().results

    assert elbv2_application.cache_interval == 300
    assert elbv2_application.name == "elbv2_application"
    assert len(elbv2_application_results) == len(found_instances)
    for result in elbv2_application_results:
        assert result.piggyback_hostname != ''
        # 20 metrics
        assert len(result.content) == 20


@pytest.mark.parametrize("names,tags,found_instances,found_instances_with_labels", elbv2_params)
def test_agent_aws_elbv2_network(get_elbv2_sections, names, tags, found_instances,
                                 found_instances_with_labels):
    elbv2_limits, elbv2_summary, _elbv2_labels, _elbv2_target_groups, _elbv2_application, elbv2_network = get_elbv2_sections(
        names, tags)
    _elbv2_limits_results = elbv2_limits.run().results
    _elbv2_summary_results = elbv2_summary.run().results
    elbv2_network_results = elbv2_network.run().results

    assert elbv2_network.cache_interval == 300
    assert elbv2_network.name == "elbv2_network"
    assert len(elbv2_network_results) == len(found_instances)
    for result in elbv2_network_results:
        assert result.piggyback_hostname != ''
        # 14 metrics
        assert len(result.content) == 14


@pytest.mark.parametrize("tags,found_instances,found_instances_with_labels", elbv2_tags_params)
def test_agent_aws_elbv2_summary_without_limits(get_elbv2_sections, tags, found_instances,
                                                found_instances_with_labels):
    _elbv2_limits, elbv2_summary, _elbv2_labels, _elbv2_target_groups, _elbv2_application, _elbv2_network = get_elbv2_sections(
        None, tags)
    elbv2_summary_results = elbv2_summary.run().results

    assert elbv2_summary.cache_interval == 300
    assert elbv2_summary.name == "elbv2_summary"

    if found_instances:
        assert len(elbv2_summary_results) == 1
        elbv2_summary_result = elbv2_summary_results[0]
        assert elbv2_summary_result.piggyback_hostname == ''
        assert len(elbv2_summary_result.content) == len(found_instances)

    else:
        assert len(elbv2_summary_results) == 0


@pytest.mark.parametrize("tags,found_instances,found_instances_with_labels", elbv2_tags_params)
def test_agent_aws_elbv2_labels_without_limits(get_elbv2_sections, tags, found_instances,
                                               found_instances_with_labels):
    _elbv2_limits, elbv2_summary, elbv2_labels, _elbv2_target_groups, _elbv2_health, _elbv2 = get_elbv2_sections(
        None, tags)
    _elbv2_summary_results = elbv2_summary.run().results
    elbv2_labels_results = elbv2_labels.run().results

    assert elbv2_labels.cache_interval == 300
    assert elbv2_labels.name == "elbv2_generic_labels"
    assert len(elbv2_labels_results) == len(found_instances_with_labels)
    for result in elbv2_labels_results:
        assert result.piggyback_hostname != ''


@pytest.mark.parametrize("tags,found_instances,found_instances_with_labels", elbv2_tags_params)
def test_agent_aws_elbv2_target_groups_without_limits(get_elbv2_sections, tags, found_instances,
                                                      found_instances_with_labels):
    _elbv2_limits, elbv2_summary, _elbv2_labels, elbv2_target_groups, _elbv2_application, _elbv2_network = get_elbv2_sections(
        None, tags)
    _elbv2_summary_results = elbv2_summary.run().results
    elbv2_target_groups_results = elbv2_target_groups.run().results

    assert elbv2_target_groups.cache_interval == 300
    assert elbv2_target_groups.name == "elbv2_target_groups"
    assert len(elbv2_target_groups_results) == len(found_instances)
    for result in elbv2_target_groups_results:
        assert result.piggyback_hostname != ''


@pytest.mark.parametrize("tags,found_instances,found_instances_with_labels", elbv2_tags_params)
def test_agent_aws_elbv2_application_without_limits(get_elbv2_sections, tags, found_instances,
                                                    found_instances_with_labels):
    _elbv2_limits, elbv2_summary, _elbv2_labels, _elbv2_target_groups, elbv2_application, _elbv2_network = get_elbv2_sections(
        None, tags)
    _elbv2_summary_results = elbv2_summary.run().results
    elbv2_application_results = elbv2_application.run().results

    assert elbv2_application.cache_interval == 300
    assert elbv2_application.name == "elbv2_application"
    assert len(elbv2_application_results) == len(found_instances)
    for result in elbv2_application_results:
        assert result.piggyback_hostname != ''
        # 20 metrics
        assert len(result.content) == 20


@pytest.mark.parametrize("tags,found_instances,found_instances_with_labels", elbv2_tags_params)
def test_agent_aws_elbv2_network_without_limits(get_elbv2_sections, tags, found_instances,
                                                found_instances_with_labels):
    _elbv2_limits, elbv2_summary, _elbv2_labels, _elbv2_target_groups, _elbv2_application, elbv2_network = get_elbv2_sections(
        None, tags)
    _elbv2_summary_results = elbv2_summary.run().results
    elbv2_network_results = elbv2_network.run().results

    assert elbv2_network.cache_interval == 300
    assert elbv2_network.name == "elbv2_network"
    assert len(elbv2_network_results) == len(found_instances)
    for result in elbv2_network_results:
        assert result.piggyback_hostname != ''
        # 14 metrics
        assert len(result.content) == 14
