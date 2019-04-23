# encoding: utf-8

import pytest

from cmk.special_agents.agent_aws import (
    AWSConfig,
    ResultDistributor,
    RDSLimits,
    RDSSummary,
    RDS,
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


class FakeCloudwatchClient(object):
    def get_metric_data(self, MetricDataQueries, StartTime='START', EndTime='END'):
        results = []
        for query in MetricDataQueries:
            results.append({
                'Id': query['Id'],
                'Label': query['Label'],
                'Timestamps': ["1970-01-01",],
                'Values': [123.0,],
                'StatusCode': "'Complete' | 'InternalError' | 'PartialData'",
                'Messages': [{
                    'Code': 'string1',
                    'Value': 'string1'
                },]
            })
        return {
            'MetricDataResults': results,
            'NextToken': 'string',
            'Messages': [{
                'Code': 'string',
                'Value': 'string'
            },]
        }


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
            'DBInstances': [
                {
                    'DBInstanceIdentifier': 'string1',
                    'DBInstanceClass': 'string1',
                    'Engine': 'string1',
                    'DBInstanceStatus': 'string1',
                    'MasterUsername': 'string1',
                    'DBName': 'string1',
                    'Endpoint': {
                        'Address': 'string1',
                        'Port': 123,
                        'HostedZoneId': 'string1'
                    },
                    'AllocatedStorage': 123,
                    'InstanceCreateTime': "1970-01-01",
                    'PreferredBackupWindow': 'string1',
                    'BackupRetentionPeriod': 123,
                    'DBSecurityGroups': [{
                        'DBSecurityGroupName': 'string1',
                        'Status': 'string1'
                    },],
                    'VpcSecurityGroups': [{
                        'VpcSecurityGroupId': 'string1',
                        'Status': 'string1'
                    },],
                    'DBParameterGroups': [{
                        'DBParameterGroupName': 'string1',
                        'ParameterApplyStatus': 'string1'
                    },],
                    'AvailabilityZone': 'string1',
                    'DBSubnetGroup': {
                        'DBSubnetGroupName': 'string1',
                        'DBSubnetGroupDescription': 'string1',
                        'VpcId': 'string1',
                        'SubnetGroupStatus': 'string1',
                        'Subnets': [{
                            'SubnetIdentifier': 'string1',
                            'SubnetAvailabilityZone': {
                                'Name': 'string1'
                            },
                            'SubnetStatus': 'string1'
                        },],
                        'DBSubnetGroupArn': 'string1'
                    },
                    'PreferredMaintenanceWindow': 'string1',
                    'PendingModifiedValues': {
                        'DBInstanceClass': 'string1',
                        'AllocatedStorage': 123,
                        'MasterUserPassword': 'string1',
                        'Port': 123,
                        'BackupRetentionPeriod': 123,
                        'MultiAZ': "True|False",
                        'EngineVersion': 'string1',
                        'LicenseModel': 'string1',
                        'Iops': 123,
                        'DBInstanceIdentifier': 'string1',
                        'StorageType': 'string1',
                        'CACertificateIdentifier': 'string1',
                        'DBSubnetGroupName': 'string1',
                        'PendingCloudwatchLogsExports': {
                            'LogTypesToEnable': ['string1',],
                            'LogTypesToDisable': ['string1',]
                        },
                        'ProcessorFeatures': [{
                            'Name': 'string1',
                            'Value': 'string1'
                        },]
                    },
                    'LatestRestorableTime': "1970-01-01",
                    'MultiAZ': "True|False",
                    'EngineVersion': 'string1',
                    'AutoMinorVersionUpgrade': "True|False",
                    'ReadReplicaSourceDBInstanceIdentifier': 'string1',
                    'ReadReplicaDBInstanceIdentifiers': ['string1',],
                    'ReadReplicaDBClusterIdentifiers': ['string1',],
                    'LicenseModel': 'string1',
                    'Iops': 123,
                    'OptionGroupMemberships': [{
                        'OptionGroupName': 'string1',
                        'Status': 'string1'
                    },],
                    'CharacterSetName': 'string1',
                    'SecondaryAvailabilityZone': 'string1',
                    'PubliclyAccessible': "True|False",
                    'StatusInfos': [{
                        'StatusType': 'string1',
                        'Normal': "True|False",
                        'Status': 'string1',
                        'Message': 'string1'
                    },],
                    'StorageType': 'string1',
                    'TdeCredentialArn': 'string1',
                    'DbInstancePort': 123,
                    'DBClusterIdentifier': 'string1',
                    'StorageEncrypted': "True|False",
                    'KmsKeyId': 'string1',
                    'DbiResourceId': 'string1',
                    'CACertificateIdentifier': 'string1',
                    'DomainMemberships': [{
                        'Domain': 'string1',
                        'Status': 'string1',
                        'FQDN': 'string1',
                        'IAMRoleName': 'string1'
                    },],
                    'CopyTagsToSnapshot': "True|False",
                    'MonitoringInterval': 123,
                    'EnhancedMonitoringResourceArn': 'string1',
                    'MonitoringRoleArn': 'string1',
                    'PromotionTier': 123,
                    'DBInstanceArn': 'string1',
                    'Timezone': 'string1',
                    'IAMDatabaseAuthenticationEnabled': "True|False",
                    'PerformanceInsightsEnabled': "True|False",
                    'PerformanceInsightsKMSKeyId': 'string1',
                    'PerformanceInsightsRetentionPeriod': 123,
                    'EnabledCloudwatchLogsExports': ['string1',],
                    'ProcessorFeatures': [{
                        'Name': 'string1',
                        'Value': 'string1'
                    },],
                    'DeletionProtection': "True|False",
                    'AssociatedRoles': [{
                        'RoleArn': 'string1',
                        'FeatureName': 'string1',
                        'Status': 'string1'
                    },],
                    'ListenerEndpoint': {
                        'Address': 'string1',
                        'Port': 123,
                        'HostedZoneId': 'string1'
                    }
                },
                {
                    'DBInstanceIdentifier': 'string2',
                    'DBInstanceClass': 'string2',
                    'Engine': 'string2',
                    'DBInstanceStatus': 'string2',
                    'MasterUsername': 'string2',
                    'DBName': 'string2',
                    'Endpoint': {
                        'Address': 'string2',
                        'Port': 123,
                        'HostedZoneId': 'string2'
                    },
                    'AllocatedStorage': 123,
                    'InstanceCreateTime': "1970-01-01",
                    'PreferredBackupWindow': 'string2',
                    'BackupRetentionPeriod': 123,
                    'DBSecurityGroups': [{
                        'DBSecurityGroupName': 'string2',
                        'Status': 'string2'
                    },],
                    'VpcSecurityGroups': [{
                        'VpcSecurityGroupId': 'string2',
                        'Status': 'string2'
                    },],
                    'DBParameterGroups': [{
                        'DBParameterGroupName': 'string2',
                        'ParameterApplyStatus': 'string2'
                    },],
                    'AvailabilityZone': 'string2',
                    'DBSubnetGroup': {
                        'DBSubnetGroupName': 'string2',
                        'DBSubnetGroupDescription': 'string2',
                        'VpcId': 'string2',
                        'SubnetGroupStatus': 'string2',
                        'Subnets': [{
                            'SubnetIdentifier': 'string2',
                            'SubnetAvailabilityZone': {
                                'Name': 'string2'
                            },
                            'SubnetStatus': 'string2'
                        },],
                        'DBSubnetGroupArn': 'string2'
                    },
                    'PreferredMaintenanceWindow': 'string2',
                    'PendingModifiedValues': {
                        'DBInstanceClass': 'string2',
                        'AllocatedStorage': 123,
                        'MasterUserPassword': 'string2',
                        'Port': 123,
                        'BackupRetentionPeriod': 123,
                        'MultiAZ': "True|False",
                        'EngineVersion': 'string2',
                        'LicenseModel': 'string2',
                        'Iops': 123,
                        'DBInstanceIdentifier': 'string2',
                        'StorageType': 'string2',
                        'CACertificateIdentifier': 'string2',
                        'DBSubnetGroupName': 'string2',
                        'PendingCloudwatchLogsExports': {
                            'LogTypesToEnable': ['string2',],
                            'LogTypesToDisable': ['string2',]
                        },
                        'ProcessorFeatures': [{
                            'Name': 'string2',
                            'Value': 'string2'
                        },]
                    },
                    'LatestRestorableTime': "1970-01-01",
                    'MultiAZ': "True|False",
                    'EngineVersion': 'string2',
                    'AutoMinorVersionUpgrade': "True|False",
                    'ReadReplicaSourceDBInstanceIdentifier': 'string2',
                    'ReadReplicaDBInstanceIdentifiers': ['string2',],
                    'ReadReplicaDBClusterIdentifiers': ['string2',],
                    'LicenseModel': 'string2',
                    'Iops': 123,
                    'OptionGroupMemberships': [{
                        'OptionGroupName': 'string2',
                        'Status': 'string2'
                    },],
                    'CharacterSetName': 'string2',
                    'SecondaryAvailabilityZone': 'string2',
                    'PubliclyAccessible': "True|False",
                    'StatusInfos': [{
                        'StatusType': 'string2',
                        'Normal': "True|False",
                        'Status': 'string2',
                        'Message': 'string2'
                    },],
                    'StorageType': 'string2',
                    'TdeCredentialArn': 'string2',
                    'DbInstancePort': 123,
                    'DBClusterIdentifier': 'string2',
                    'StorageEncrypted': "True|False",
                    'KmsKeyId': 'string2',
                    'DbiResourceId': 'string2',
                    'CACertificateIdentifier': 'string2',
                    'DomainMemberships': [{
                        'Domain': 'string2',
                        'Status': 'string2',
                        'FQDN': 'string2',
                        'IAMRoleName': 'string2'
                    },],
                    'CopyTagsToSnapshot': "True|False",
                    'MonitoringInterval': 123,
                    'EnhancedMonitoringResourceArn': 'string2',
                    'MonitoringRoleArn': 'string2',
                    'PromotionTier': 123,
                    'DBInstanceArn': 'string2',
                    'Timezone': 'string2',
                    'IAMDatabaseAuthenticationEnabled': "True|False",
                    'PerformanceInsightsEnabled': "True|False",
                    'PerformanceInsightsKMSKeyId': 'string2',
                    'PerformanceInsightsRetentionPeriod': 123,
                    'EnabledCloudwatchLogsExports': ['string2',],
                    'ProcessorFeatures': [{
                        'Name': 'string2',
                        'Value': 'string2'
                    },],
                    'DeletionProtection': "True|False",
                    'AssociatedRoles': [{
                        'RoleArn': 'string2',
                        'FeatureName': 'string2',
                        'Status': 'string2'
                    },],
                    'ListenerEndpoint': {
                        'Address': 'string2',
                        'Port': 123,
                        'HostedZoneId': 'string2'
                    }
                },
            ]
        }


#.


def test_agent_aws_rds_limits():
    region = 'region'
    config = AWSConfig('hostname', (None, None))

    rds_limits = RDSLimits(FakeRDSClient(), region, config)
    rds_limits_results = rds_limits.run().results

    #--RDSLimits------------------------------------------------------------
    assert rds_limits.interval == 300
    assert rds_limits.name == "rds_limits"

    assert len(rds_limits_results) == 1

    rds_limits_result = rds_limits_results[0]
    assert rds_limits_result.piggyback_hostname == ''
    assert len(rds_limits_result.content) == 15


def test_agent_aws_rds_result_distribution():
    region = 'region'
    config = AWSConfig('hostname', (None, None))
    config.add_single_service_config('rds_names', None)
    config.add_service_tags('rds_tags', (None, None))

    fake_rds_client = FakeRDSClient()
    fake_cloudwatch_client = FakeCloudwatchClient()

    rds_summary_distributor = ResultDistributor()

    rds_summary = RDSSummary(fake_rds_client, region, config, rds_summary_distributor)
    rds = RDS(fake_cloudwatch_client, region, config)

    rds_summary_distributor.add(rds)

    rds_summary_results = rds_summary.run().results
    rds_results = rds.run().results

    #--RDSSummary-----------------------------------------------------------
    assert rds_summary.interval == 300
    assert rds_summary.name == "rds_summary"
    assert len(rds_summary_results) == 1

    rds_summary_result = rds_summary_results[0]
    assert rds_summary_result.piggyback_hostname == ''
    assert len(rds_summary_result.content) == 2

    #--RDS------------------------------------------------------------------
    assert rds.interval == 300
    assert rds.name == "rds"

    assert len(rds_results) == 1

    rds_result = rds_results[0]
    assert rds_result.piggyback_hostname == ''
    # 21 (metrics) * X (DBs) == Y (len results)
    assert len(rds_result.content) == 21 * 2
