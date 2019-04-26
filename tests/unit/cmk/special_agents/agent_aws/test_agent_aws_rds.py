# pylint: disable=redefined-outer-name

import pytest
from agent_aws_fake_clients import (
    RDSDescribeDBInstancesIB,
    FakeCloudwatchClient,
)

from cmk.special_agents.agent_aws import (
    AWSConfig,
    ResultDistributor,
    RDSLimits,
    RDSSummary,
    RDS,
)


class FakeRDSClient(object):
    def describe_account_attributes(self):
        return {
            'AccountQuotas': [
                {
                    'AccountQuotaName': 'unused',
                    'Used': 1,
                    'Max': 2,
                },
                {
                    'AccountQuotaName': 'DBClusters',
                    'Used': 1,
                    'Max': 2,
                },
                {
                    'AccountQuotaName': 'DBClusterParameterGroups',
                    'Used': 1,
                    'Max': 2,
                },
                {
                    'AccountQuotaName': 'DBInstances',
                    'Used': 1,
                    'Max': 2,
                },
                {
                    'AccountQuotaName': 'EventSubscriptions',
                    'Used': 1,
                    'Max': 2,
                },
                {
                    'AccountQuotaName': 'ManualSnapshots',
                    'Used': 1,
                    'Max': 2,
                },
                {
                    'AccountQuotaName': 'OptionGroups',
                    'Used': 1,
                    'Max': 2,
                },
                {
                    'AccountQuotaName': 'DBParameterGroups',
                    'Used': 1,
                    'Max': 2,
                },
                {
                    'AccountQuotaName': 'ReadReplicasPerMaster',
                    'Used': 1,
                    'Max': 2,
                },
                {
                    'AccountQuotaName': 'ReservedDBInstances',
                    'Used': 1,
                    'Max': 2,
                },
                {
                    'AccountQuotaName': 'DBSecurityGroups',
                    'Used': 1,
                    'Max': 2,
                },
                {
                    'AccountQuotaName': 'DBSubnetGroups',
                    'Used': 1,
                    'Max': 2,
                },
                {
                    'AccountQuotaName': 'SubnetsPerDBSubnetGroup',
                    'Used': 1,
                    'Max': 2,
                },
                {
                    'AccountQuotaName': 'AllocatedStorage',
                    'Used': 1,
                    'Max': 2,
                },
                {
                    'AccountQuotaName': 'AuthorizationsPerDBSecurityGroup',
                    'Used': 1,
                    'Max': 2,
                },
                {
                    'AccountQuotaName': 'DBClusterRoles',
                    'Used': 1,
                    'Max': 2,
                },
            ]
        }

    def describe_db_instances(self, DBInstanceIdentifier=None, Filters=None):
        return {
            'Marker': 'string',
            'DBInstances': RDSDescribeDBInstancesIB.create_instances(amount=2),
        }


@pytest.fixture()
def get_rds_sections():
    def _create_rds_sections():
        region = 'region'
        config = AWSConfig('hostname', (None, None))
        config.add_single_service_config('rds_names', None)
        config.add_service_tags('rds_tags', (None, None))

        fake_rds_client = FakeRDSClient()
        fake_cloudwatch_client = FakeCloudwatchClient()

        rds_summary_distributor = ResultDistributor()

        rds_limits = RDSLimits(FakeRDSClient(), region, config)
        rds_summary = RDSSummary(fake_rds_client, region, config, rds_summary_distributor)
        rds = RDS(fake_cloudwatch_client, region, config)

        rds_summary_distributor.add(rds)
        return rds_limits, rds_summary, rds

    return _create_rds_sections


def test_agent_aws_rds_limits(get_rds_sections):
    rds_limits, _rds_summary, _rds = get_rds_sections()
    rds_limits_results = rds_limits.run().results

    assert rds_limits.cache_interval == 300
    assert rds_limits.name == "rds_limits"

    assert len(rds_limits_results) == 1

    rds_limits_result = rds_limits_results[0]
    assert rds_limits_result.piggyback_hostname == ''
    assert len(rds_limits_result.content) == 15


def test_agent_aws_rds_summary(get_rds_sections):
    _rds_limits, rds_summary, _rds = get_rds_sections()
    rds_summary_results = rds_summary.run().results

    assert rds_summary.cache_interval == 300
    assert rds_summary.name == "rds_summary"
    assert len(rds_summary_results) == 1

    rds_summary_result = rds_summary_results[0]
    assert rds_summary_result.piggyback_hostname == ''
    assert len(rds_summary_result.content) == 2


def test_agent_aws_rds(get_rds_sections):
    _rds_limits, rds_summary, rds = get_rds_sections()
    _rds_summary_results = rds_summary.run().results
    rds_results = rds.run().results

    assert rds.cache_interval == 300
    assert rds.name == "rds"

    assert len(rds_results) == 1

    rds_result = rds_results[0]
    assert rds_result.piggyback_hostname == ''
    # 21 (metrics) * X (DBs) == Y (len results)
    assert len(rds_result.content) == 21 * 2
