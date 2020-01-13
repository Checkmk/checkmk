# pylint: disable=redefined-outer-name

import pytest
from agent_aws_fake_clients import (
    FakeCloudwatchClient,
    FakeServiceQuotasClient,
    EC2DescribeInstancesIB,
    EC2DescribeReservedInstancesIB,
    EC2DescribeAddressesIB,
    EC2DescribeSecurityGroupsIB,
    EC2DescribeNetworkInterfacesIB,
    EC2DescribeSpotInstanceRequestsIB,
    EC2DescribeSpotFleetRequestsIB,
    EC2DescribeTagsIB,
)

from cmk.special_agents.agent_aws import (
    AWSConfig,
    ResultDistributor,
    EC2Limits,
    EC2Summary,
    EC2Labels,
    EC2SecurityGroups,
    EC2,
)


class FakeEC2Client(object):
    def describe_instances(self, InstanceIds=None, Filters=None):
        return {
            'Reservations': [{
                'Groups': [{
                    'GroupName': 'string',
                    'GroupId': 'string'
                },],
                'Instances': EC2DescribeInstancesIB.create_instances(amount=3),
                'OwnerId': 'string',
                'RequesterId': 'string',
                'ReservationId': 'string'
            },],
            'NextToken': 'string'
        }

    def describe_reserved_instances(self):
        return {
            'ReservedInstances': EC2DescribeReservedInstancesIB.create_instances(amount=3),
        }

    def describe_addresses(self):
        return {
            'Addresses': EC2DescribeAddressesIB.create_instances(amount=3),
        }

    def describe_security_groups(self, InstanceIds=None, Filters=None):
        return {
            'SecurityGroups': EC2DescribeSecurityGroupsIB.create_instances(amount=3),
            'NextToken': 'string',
        }

    def describe_network_interfaces(self):
        return {
            'NetworkInterfaces': EC2DescribeNetworkInterfacesIB.create_instances(amount=3),
            'NextToken': 'string',
        }

    def describe_spot_instance_requests(self):
        return {
            'SpotInstanceRequests': EC2DescribeSpotInstanceRequestsIB.create_instances(amount=3),
            'NextToken': 'string',
        }

    def describe_spot_fleet_requests(self):
        return {
            'SpotFleetRequestConfigs': EC2DescribeSpotFleetRequestsIB.create_instances(amount=3),
            'NextToken': 'string',
        }

    def describe_tags(self, Filters=None):
        tags = []
        for filter_ in Filters:
            for value in filter_['Values']:
                if value == 'InstanceId-0':
                    tags = EC2DescribeTagsIB.create_instances(amount=1)
                    break
        for tag in tags:
            tag['ResourceId'] = tag['ResourceId'].replace('ResourceId', 'InstanceId')
        return {
            'Tags': tags,
            'NextToken': 'string',
        }


@pytest.fixture()
def get_ec2_sections():
    def _create_ec2_sections(names, tags):
        region = 'region'
        config = AWSConfig('hostname', [], (None, None))
        config.add_single_service_config('ec2_names', names)
        config.add_service_tags('ec2_tags', tags)

        fake_ec2_client = FakeEC2Client()
        fake_cloudwatch_client = FakeCloudwatchClient()
        fake_service_quotas_client = FakeServiceQuotasClient()

        ec2_limits_distributor = ResultDistributor()
        ec2_summary_distributor = ResultDistributor()

        ec2_limits = EC2Limits(fake_ec2_client, region, config, ec2_limits_distributor,
                               fake_service_quotas_client)
        ec2_summary = EC2Summary(fake_ec2_client, region, config, ec2_summary_distributor)
        ec2_labels = EC2Labels(fake_ec2_client, region, config)
        ec2_security_groups = EC2SecurityGroups(fake_ec2_client, region, config)
        ec2 = EC2(fake_cloudwatch_client, region, config)

        ec2_limits_distributor.add(ec2_summary)
        ec2_summary_distributor.add(ec2_labels)
        ec2_summary_distributor.add(ec2_security_groups)
        ec2_summary_distributor.add(ec2)
        return ec2_limits, ec2_summary, ec2_labels, ec2_security_groups, ec2

    return _create_ec2_sections


ec2_params = [
    (None, (None, None), 3, 1),
    (None, ([['Key-0']], [['Value-0']]), 3, 1),
    (None, ([['Key-X']], [['Value-0']]), 0, 0),
    (None, ([['Key-0']], [['Value-X']]), 0, 0),
    (None, ([['Key-0']], [['Value-1']]), 0, 0),
    (None, ([['Key-1']], [['Value-0', 'Value-1']]), 3, 1),
    (None, ([['Key-0']], [['Value-0', 'Value-1']]), 3, 1),
    (['InstanceId-0'], (None, None), 1, 1),
    (['InstanceId-0', 'Foo', 'Bar'], (None, None), 1, 1),
    (['InstanceId-0', 'InstanceId-1'], (None, None), 2, 1),
    (['InstanceId-0', 'InstanceId-1', 'Foo', 'Bar'], (None, None), 2, 1),
    (['InstanceId-0', 'InstanceId-1', 'InstanceId-2'], (None, None), 3, 1),
    (['InstanceId-0', 'InstanceId-1', 'InstanceId-2', 'Foo', 'Bar'], (None, None), 3, 1),
    (['Foo', 'Bar'], (None, None), 0, 0),
]


@pytest.mark.parametrize("names,tags,found_ec2,found_ec2_with_labels", ec2_params)
def test_agent_aws_ec2_limits(get_ec2_sections, names, tags, found_ec2, found_ec2_with_labels):
    ec2_limits, _ec2_summary, _ec2_labels, _ec2_security_groups, _ec2 = get_ec2_sections(
        names, tags)
    ec2_limits_results = ec2_limits.run().results

    assert ec2_limits.cache_interval == 300
    assert ec2_limits.name == "ec2_limits"

    # 3 instances and one additional result (global limits)
    assert len(ec2_limits_results) == 4

    for result in ec2_limits_results:
        for limit in result.content:
            if result.piggyback_hostname == "":
                assert limit.key in [
                            'vpc_elastic_ip_addresses',
                            'elastic_ip_addresses',
                            'spot_inst_requests',
                            'active_spot_fleet_requests',
                            'spot_fleet_total_target_capacity',]\
                       or limit.key.startswith('running_ondemand_instances_')
            else:
                assert limit.key in [
                    'vpc_sec_group_rules',
                    'vpc_sec_groups',
                    'if_vpc_sec_group',
                ]


@pytest.mark.parametrize("names,tags,found_ec2,found_ec2_with_labels", ec2_params)
def test_agent_aws_ec2_summary(get_ec2_sections, names, tags, found_ec2, found_ec2_with_labels):
    ec2_limits, ec2_summary, _ec2_labels, _ec2_security_groups, _ec2 = get_ec2_sections(names, tags)
    _ec2_limits_results = ec2_limits.run().results
    ec2_summary_results = ec2_summary.run().results

    assert ec2_summary.cache_interval == 300
    assert ec2_summary.name == "ec2_summary"

    if found_ec2:
        assert len(ec2_summary_results) == 1

        result = ec2_summary_results[0]
        assert result.piggyback_hostname == ""
        assert len(result.content) == found_ec2

    else:
        assert len(ec2_summary_results) == 0


@pytest.mark.parametrize("names,tags,found_ec2,found_ec2_with_labels", ec2_params)
def test_agent_aws_ec2_labels(get_ec2_sections, names, tags, found_ec2, found_ec2_with_labels):
    ec2_limits, ec2_summary, ec2_labels, _ec2_security_groups, _ec2 = get_ec2_sections(names, tags)
    _ec2_limits_results = ec2_limits.run().results
    _ec2_summary_results = ec2_summary.run().results
    ec2_labels_results = ec2_labels.run().results

    assert ec2_labels.cache_interval == 300
    assert ec2_labels.name == "ec2_labels"

    assert len(ec2_labels_results) == found_ec2_with_labels


@pytest.mark.parametrize("names,tags,found_ec2,found_ec2_with_labels", ec2_params)
def test_agent_aws_ec2_security_groups(get_ec2_sections, names, tags, found_ec2,
                                       found_ec2_with_labels):
    ec2_limits, ec2_summary, _ec2_labels, ec2_security_groups, _ec2 = get_ec2_sections(names, tags)
    _ec2_limits_results = ec2_limits.run().results
    _ec2_summary_results = ec2_summary.run().results
    ec2_security_groups_results = ec2_security_groups.run().results

    assert ec2_security_groups.cache_interval == 300
    assert ec2_security_groups.name == "ec2_security_groups"

    assert len(ec2_security_groups_results) == found_ec2

    for result in ec2_security_groups_results:
        assert result.piggyback_hostname != ''


@pytest.mark.parametrize("names,tags,found_ec2,found_ec2_with_labels", ec2_params)
def test_agent_aws_ec2(get_ec2_sections, names, tags, found_ec2, found_ec2_with_labels):
    ec2_limits, ec2_summary, _ec2_labels, _ec2_security_groups, ec2 = get_ec2_sections(names, tags)
    _ec2_limits_results = ec2_limits.run().results
    _ec2_summary_results = ec2_summary.run().results
    ec2_results = ec2.run().results

    assert ec2.cache_interval == 300
    assert ec2.name == "ec2"

    assert len(ec2_results) == found_ec2

    for result in ec2_results:
        assert result.piggyback_hostname != ''

        # 11 metrics
        assert len(result.content) == 11


def test_agent_aws_ec2_summary_without_limits(get_ec2_sections):
    _ec2_limits, ec2_summary, _ec2_labels, _ec2_security_groups, _ec2 = get_ec2_sections(
        None, (None, None))
    ec2_summary_results = ec2_summary.run().results

    assert ec2_summary.cache_interval == 300
    assert ec2_summary.name == "ec2_summary"

    assert len(ec2_summary_results) == 1

    result = ec2_summary_results[0]
    assert result.piggyback_hostname == ""
    assert len(result.content) == 3


def test_agent_aws_ec2_labels_without_limits(get_ec2_sections):
    _ec2_limits, ec2_summary, ec2_labels, _ec2_security_groups, _ec2 = get_ec2_sections(
        None, (None, None))
    _ec2_summary_results = ec2_summary.run().results
    ec2_labels_results = ec2_labels.run().results

    assert ec2_labels.cache_interval == 300
    assert ec2_labels.name == "ec2_labels"

    assert len(ec2_labels_results) == 1


def test_agent_aws_ec2_security_groups_without_limits(get_ec2_sections):
    _ec2_limits, ec2_summary, _ec2_labels, ec2_security_groups, _ec2 = get_ec2_sections(
        None, (None, None))
    _ec2_summary_results = ec2_summary.run().results
    ec2_security_groups_results = ec2_security_groups.run().results

    assert ec2_security_groups.cache_interval == 300
    assert ec2_security_groups.name == "ec2_security_groups"

    assert len(ec2_security_groups_results) == 3

    for result in ec2_security_groups_results:
        assert result.piggyback_hostname != ''


def test_agent_aws_ec2_without_limits(get_ec2_sections):
    _ec2_limits, ec2_summary, _ec2_labels, _ec2_security_groups, ec2 = get_ec2_sections(
        None, (None, None))
    _ec2_summary_results = ec2_summary.run().results
    ec2_results = ec2.run().results

    assert ec2.cache_interval == 300
    assert ec2.name == "ec2"

    assert len(ec2_results) == 3

    for result in ec2_results:
        assert result.piggyback_hostname != ''

        # 11 metrics
        assert len(result.content) == 11
