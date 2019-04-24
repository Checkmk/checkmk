# pylint: disable=redefined-outer-name

import pytest
from agent_aws_fake_clients import (
    FakeCloudwatchClient,
    EC2DescribeInstancesIC,
    EC2DescribeVolumesIC,
    EC2DescribeSnapshotsIC,
    EC2DescribeVolumeStatusIC,
)

from cmk.special_agents.agent_aws import (
    AWSConfig,
    ResultDistributor,
    EC2Summary,
    EBSLimits,
    EBSSummary,
    EBS,
)


class FakeEC2Client(object):
    def describe_instances(self, Filters=None, InstanceIds=None):
        return {
            'Reservations': [{
                'Groups': [{
                    'GroupName': 'string',
                    'GroupId': 'string'
                },],
                'Instances': EC2DescribeInstancesIC.create_instances(amount=2),
                'OwnerId': 'string',
                'RequesterId': 'string',
                'ReservationId': 'string',
            },],
            'NextToken': 'string',
        }

    def describe_snapshots(self):
        return {
            'Snapshots': EC2DescribeSnapshotsIC.create_instances(amount=3),
            'NextToken': 'string',
        }

    def describe_volumes(self, VolumeIds=None, Filters=None):
        return {
            'Volumes': EC2DescribeVolumesIC.create_instances(amount=3),
            'NextToken': 'string',
        }

    def describe_volume_status(self, VolumeIds=None, Filters=None):
        return {
            'VolumeStatuses': EC2DescribeVolumeStatusIC.create_instances(amount=3),
            'NextToken': 'string',
        }


@pytest.fixture()
def get_ebs_sections():
    def _create_ebs_sections(ebs_tags):
        region = 'region'
        config = AWSConfig('hostname', (None, None))
        config.add_single_service_config('ebs_names', None)
        config.add_service_tags('ebs_tags', ebs_tags)
        config.add_single_service_config('ec2_names', None)
        config.add_service_tags('ec2_tags', (None, None))

        fake_ec2_client = FakeEC2Client()
        fake_cloudwatch_client = FakeCloudwatchClient()

        ec2_summary_distributor = ResultDistributor()
        ebs_limits_distributor = ResultDistributor()
        ebs_summary_distributor = ResultDistributor()

        ec2_summary = EC2Summary(fake_ec2_client, region, config, ec2_summary_distributor)
        ebs_limits = EBSLimits(fake_ec2_client, region, config, ebs_limits_distributor)
        ebs_summary = EBSSummary(fake_ec2_client, region, config, ebs_summary_distributor)
        ebs = EBS(fake_cloudwatch_client, region, config)

        ec2_summary_distributor.add(ebs_summary)
        ebs_limits_distributor.add(ebs_summary)
        ebs_summary_distributor.add(ebs)
        return ec2_summary, ebs_limits, ebs_summary, ebs

    return _create_ebs_sections


ebs_params = [
    ((None, None), 3),
    (([['Key-0']], [['Value-0']]), 3),
    (([['Key-0']], [['Value-X']]), 0),
    (([['Key-X']], [['Value-X']]), 0),
]


@pytest.mark.parametrize("ebs_tags,found_ebs", ebs_params)
def test_agent_aws_ebs_limits(get_ebs_sections, ebs_tags, found_ebs):
    ec2_summary, ebs_limits, _ebs_summary, _ebs = get_ebs_sections(ebs_tags)
    _ec2_summary_results = ec2_summary.run().results
    ebs_limits_results = ebs_limits.run().results

    assert ebs_limits.interval == 300
    assert ebs_limits.name == "ebs_limits"

    assert len(ebs_limits_results) == 1

    ebs_limits_result = ebs_limits_results[0]
    assert ebs_limits_result.piggyback_hostname == ''
    assert len(ebs_limits_result.content) == 7

    for limit in ebs_limits_result.content:
        assert limit.key in [
            'block_store_snapshots',
            'block_store_space_standard',
            'block_store_space_io1',
            'block_store_iops_io1',
            'block_store_space_gp2',
            'block_store_space_sc1',
            'block_store_space_st1',
        ]


@pytest.mark.parametrize("ebs_tags,found_ebs", ebs_params)
def test_agent_aws_ebs_summary(get_ebs_sections, ebs_tags, found_ebs):
    ec2_summary, ebs_limits, ebs_summary, _ebs = get_ebs_sections(ebs_tags)
    _ec2_summary_results = ec2_summary.run().results
    _ebs_limits_results = ebs_limits.run().results
    ebs_summary_results = ebs_summary.run().results

    assert ebs_summary.interval == 300
    assert ebs_summary.name == "ebs_summary"

    assert len(ebs_summary_results) == found_ebs


@pytest.mark.parametrize("ebs_tags,found_ebs", ebs_params)
def test_agent_aws_ebs(get_ebs_sections, ebs_tags, found_ebs):
    ec2_summary, ebs_limits, ebs_summary, ebs = get_ebs_sections(ebs_tags)
    _ec2_summary_results = ec2_summary.run().results
    _ebs_limits_results = ebs_limits.run().results
    _ebs_summary_results = ebs_summary.run().results
    ebs_results = ebs.run().results

    assert ebs.interval == 300
    assert ebs.name == "ebs"

    assert len(ebs_results) == found_ebs

    if found_ebs:
        ebs_result = ebs_results[0]
        # Y (len results) == 6 (metrics) * X (buckets)
        # But: 5 metrics for all volume types
        assert len(ebs_result.content) >= 5 * found_ebs


def test_agent_aws_ebs_summary_without_limits(get_ebs_sections):
    ec2_summary, _ebs_limits, ebs_summary, _ebs = get_ebs_sections((None, None))
    _ec2_summary_results = ec2_summary.run().results
    ebs_summary_results = ebs_summary.run().results

    assert ebs_summary.interval == 300
    assert ebs_summary.name == "ebs_summary"

    assert len(ebs_summary_results) == 3


def test_agent_aws_ebs_without_limits(get_ebs_sections):
    ec2_summary, _ebs_limits, ebs_summary, ebs = get_ebs_sections((None, None))
    _ec2_summary_results = ec2_summary.run().results
    _ebs_summary_results = ebs_summary.run().results
    ebs_results = ebs.run().results

    assert ebs.interval == 300
    assert ebs.name == "ebs"

    found_ebs = 3
    assert len(ebs_results) == found_ebs

    if found_ebs:
        ebs_result = ebs_results[0]
        # Y (len results) == 6 (metrics) * X (buckets)
        # But: 5 metrics for all volume types
        assert len(ebs_result.content) >= 5 * found_ebs
