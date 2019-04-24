#!/usr/bin/env python

import abc
import random

#   .--entities------------------------------------------------------------.
#   |                             _   _ _   _                              |
#   |                   ___ _ __ | |_(_) |_(_) ___  ___                    |
#   |                  / _ \ '_ \| __| | __| |/ _ \/ __|                   |
#   |                 |  __/ | | | |_| | |_| |  __/\__ \                   |
#   |                  \___|_| |_|\__|_|\__|_|\___||___/                   |
#   |                                                                      |
#   '----------------------------------------------------------------------'

#   ---abc------------------------------------------------------------------


class Entity(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, key):
        self.key = key

    @abc.abstractmethod
    def create(self, idx, amount):
        return


#   ---structural-----------------------------------------------------------


class List(Entity):
    def __init__(self, key, elements, from_choice=None):
        super(List, self).__init__(key)
        self._elements = elements
        self._from_choice = from_choice

    def create(self, idx, amount):
        if self._from_choice:
            list_ = []
            for choice in self._from_choice.choices:
                elem = {self._from_choice.key: choice}
                elem.update(
                    {e.key: e.create("%s-%s" % (idx, choice), amount) for e in self._elements})
                list_.append(elem)
            return list_
        return [{e.key: e.create("%s-%s" % (idx, x), amount)
                 for e in self._elements}
                for x in xrange(amount)]


class Dict(Entity):
    def __init__(self, key, values, enumerate_keys=None):
        super(Dict, self).__init__(key)
        self._values = values
        self._enumerate_keys = enumerate_keys

    def create(self, idx, amount):
        dict_ = {}
        if self._enumerate_keys:
            for x in xrange(amount):
                this_idx = "%s-%s" % (self._enumerate_keys.key, x)
                dict_.update({this_idx: self._enumerate_keys.create(this_idx, amount)})
        dict_.update({v.key: v.create(idx, amount) for v in self._values})
        return dict_


#   ---behavioural----------------------------------------------------------


class Str(Entity):
    def create(self, idx, amount):
        return "%s-%s" % (self.key, idx)


class Int(Entity):
    def create(self, idx, amount):
        return random.choice(xrange(100))


class Float(Entity):
    def create(self, idx, amount):
        return 1.0 * random.choice(xrange(100))


class Timestamp(Entity):
    def create(self, idx, amount):
        return "2019-%02d-%02d" % (
            random.choice(xrange(1, 13)),
            random.choice(xrange(1, 29)),
        )


class Enum(Entity):
    def create(self, idx, amount):
        return ['%s-%s-%s' % (self.key, idx, x) for x in xrange(amount)]


class Choice(Entity):
    def __init__(self, key, choices):
        super(Choice, self).__init__(key)
        self.choices = choices

    def create(self, idx, amount):
        return random.choice(self.choices)


class BoolChoice(Choice):
    def __init__(self, key):
        super(BoolChoice, self).__init__(key, [True, False])


#.
#   .--creators------------------------------------------------------------.
#   |                                    _                                 |
#   |                 ___ _ __ ___  __ _| |_ ___  _ __ ___                 |
#   |                / __| '__/ _ \/ _` | __/ _ \| '__/ __|                |
#   |               | (__| | |  __/ (_| | || (_) | |  \__ \                |
#   |                \___|_|  \___|\__,_|\__\___/|_|  |___/                |
#   |                                                                      |
#   '----------------------------------------------------------------------'

#   .--abc------------------------------------------------------------------


class InstanceCreator(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, idx, amount):
        self._idx = idx
        self._amount = amount
        self._inst = {}

    def add(self, value):
        self._inst[value.key] = value.create(self._idx, self._amount)

    def create(self):
        self._fill_instance()
        return self._inst

    def _fill_instance(self):
        pass

    @classmethod
    def create_instances(cls, amount):
        return [cls(idx, amount).create() for idx in xrange(amount)]


#.
#   .--S3-------------------------------------------------------------------


class S3ListBucketsInstanceCreator(InstanceCreator):
    def _fill_instance(self):
        self.add(Str('Name'))
        self.add(Timestamp('CreationDate'))


class S3BucketTaggingInstanceCreator(InstanceCreator):
    def _fill_instance(self):
        self.add(Str('Key'))
        self.add(Str('Value'))


#.
#   .--Cloudwatch-----------------------------------------------------------


class CloudwatchDescribeAlarmsInstanceCreator(InstanceCreator):
    def _fill_instance(self):
        self.add(Str('AlarmName'))
        self.add(Str('AlarmArn'))
        self.add(Str('AlarmDescription'))
        self.add(Timestamp('AlarmConfigurationUpdatedTimestamp'))
        self.add(BoolChoice('ActionsEnabled'))
        self.add(Enum('OKActions'))
        self.add(Enum('AlarmActions'))
        self.add(Enum('InsufficientDataActions'))
        self.add(Choice('StateValue', ['OK', 'ALARM', 'INSUFFICIENT_DATA']))
        self.add(Str('StateReason'))
        self.add(Str('StateReasonData'))
        self.add(Timestamp('StateUpdatedTimestamp'))
        self.add(Str('MetricName'))
        self.add(Str('Namespace'))
        self.add(Choice('Statistic', [
            'SampleCount',
            'Average',
            'Sum',
            'Minimum',
            'Maximum',
        ]))
        self.add(Str('ExtendedStatistic'))
        self.add(List('Dimensions', [
            Str('Name'),
            Str('Value'),
        ]))
        self.add(Int('Period'))
        self.add(
            Choice('Unit', [
                'Seconds',
                'Microseconds',
                'Milliseconds',
                'Bytes',
                'Kilobytes',
                'Megabytes',
                'Gigabytes',
                'Terabytes',
                'Bits',
                'Kilobits',
                'Megabits',
                'Gigabits',
                'Terabits',
                'Percent',
                'Count',
                'Bytes/Second',
                'Kilobytes/Second',
                'Megabytes/Second',
                'Gigabytes/Second',
                'Terabytes/Second',
                'Bits/Second',
                'Kilobits/Second',
                'Megabits/Second',
                'Gigabits/Second',
                'Terabits/Second',
                'Count/Second',
                'None',
            ]))
        self.add(Int('EvaluationPeriods'))
        self.add(Int('DatapointsToAlarm'))
        self.add(Float('Threshold'))
        self.add(
            Choice('ComparisonOperator', [
                'GreaterThanOrEqualToThreshold',
                'GreaterThanThreshold',
                'LessThanThreshold',
                'LessThanOrEqualToThreshold',
            ]))
        self.add(Str('TreatMissingData'))
        self.add(Str('EvaluateLowSampleCountPercentile'))
        self.add(
            List('Metrics', [
                Str('Id'),
                Dict('MetricStat', [
                    Dict('Metric', [
                        Str('Namespace'),
                        Str('MetricName'),
                        List('Dimensions', [
                            Str('Name'),
                            Str('Value'),
                        ]),
                    ]),
                    Int('Period'),
                    Str('Stat'),
                    Choice('Unit', [
                        'Seconds',
                        'Microseconds',
                        'Milliseconds',
                        'Bytes',
                        'Kilobytes',
                        'Megabytes',
                        'Gigabytes',
                        'Terabytes',
                        'Bits',
                        'Kilobits',
                        'Megabits',
                        'Gigabits',
                        'Terabits',
                        'Percent',
                        'Count',
                        'Bytes/Second',
                        'Kilobytes/Second',
                        'Megabytes/Second',
                        'Gigabytes/Second',
                        'Terabytes/Second',
                        'Bits/Second',
                        'Kilobits/Second',
                        'Megabits/Second',
                        'Gigabits/Second',
                        'Terabits/Second',
                        'Count/Second',
                        'None',
                    ])
                ]),
                Str('Expression'),
                Str('Label'),
                BoolChoice('ReturnData'),
            ]))


#.
#   .--CE-------------------------------------------------------------------


class CEGetCostsAndUsageInstanceCreator(InstanceCreator):
    def _fill_instance(self):
        self.add(Dict('TimePeriod', [
            Str('Start'),
            Str('End'),
        ]))
        self.add(Dict('Total', [Dict('string', [
            Str('Amount'),
            Str('Unit'),
        ])]))
        self.add(
            List('Groups', [
                Enum('Keys'),
                Dict('Metrics', [Dict('string', [
                    Str('Amount'),
                    Str('Unit'),
                ])]),
            ]))
        self.add(BoolChoice('Estimated'))


#.
#   .--RDS------------------------------------------------------------------


class RDSDescribeAccountAttributesInstanceCreator(InstanceCreator):
    def _fill_instance(self):
        # TODO for each choice one entry
        self.add(
            Choice('AccountQuotaName', [
                'DBClusters',
                'DBClusterParameterGroups',
                'DBInstances',
                'EventSubscriptions',
                'ManualSnapshots',
                'OptionGroups',
                'DBParameterGroups',
                'ReadReplicasPerMaster',
                'ReservedDBInstances',
                'DBSecurityGroups',
                'DBSubnetGroups',
                'SubnetsPerDBSubnetGroup',
                'AllocatedStorage',
                'AuthorizationsPerDBSecurityGroup',
                'DBClusterRoles',
            ]))
        self.add(Int('Used'))
        self.add(Int('Max'))


class RDSDescribeDBInstancesInstanceCreator(InstanceCreator):
    def _fill_instance(self):
        self.add(Str('DBInstanceIdentifier'))
        self.add(Str('DBInstanceClass'))
        self.add(Str('Engine'))
        self.add(Str('DBInstanceStatus'))
        self.add(Str('MasterUsername'))
        self.add(Str('DBName'))
        self.add(Dict('Endpoint', [
            Str('Address'),
            Int('Port'),
            Str('HostedZoneId'),
        ]))
        self.add(Int('AllocatedStorage'))
        self.add(Timestamp('InstanceCreateTime'))
        self.add(Str('PreferredBackupWindow'))
        self.add(Int('BackupRetentionPeriod'))
        self.add(List('DBSecurityGroups', [
            Str('DBSecurityGroupName'),
            Str('Status'),
        ]))
        self.add(List('VpcSecurityGroups', [
            Str('VpcSecurityGroupId'),
            Str('Status'),
        ]))
        self.add(
            List('DBParameterGroups', [
                Str('DBParameterGroupName'),
                Str('ParameterApplyStatus'),
            ]))
        self.add(Str('AvailabilityZone'))
        self.add(
            Dict('DBSubnetGroup', [
                Str('DBSubnetGroupName'),
                Str('DBSubnetGroupDescription'),
                Str('VpcId'),
                Str('SubnetGroupStatus'),
                List('Subnets', [
                    Str('SubnetIdentifier'),
                    Dict('SubnetAvailabilityZone', [
                        Str('Name'),
                    ]),
                    Str('SubnetStatus'),
                ]),
                Str('DBSubnetGroupArn'),
            ]))
        self.add(Str('PreferredMaintenanceWindow'))
        self.add(
            Dict('PendingModifiedValues', [
                Str('DBInstanceClass'),
                Int('AllocatedStorage'),
                Str('MasterUserPassword'),
                Int('Port'),
                Str('BackupRetentionPeriod'),
                BoolChoice('MultiAZ'),
                Str('EngineVersion'),
                Str('LicenseModel'),
                Int('Iops'),
                Str('DBInstanceIdentifier'),
                Str('StorageType'),
                Str('CACertificateIdentifier'),
                Str('DBSubnetGroupName'),
                Dict('PendingCloudwatchLogsExports', [
                    Enum('LogTypesToEnable'),
                    Enum('LogTypesToDisable'),
                ]),
                Dict('ProcessorFeatures', [
                    Str('Name'),
                    Str('Value'),
                ]),
            ]))
        self.add(Timestamp('LatestRestorableTime'))
        self.add(BoolChoice('MultiAZ'))
        self.add(Str('EngineVersion'))
        self.add(BoolChoice('AutoMinorVersionUpgrade'))
        self.add(Str('ReadReplicaSourceDBInstanceIdentifier'))
        self.add(Enum('ReadReplicaDBInstanceIdentifiers'))
        self.add(Enum('ReadReplicaDBClusterIdentifiers'))
        self.add(Str('LicenseModel'))
        self.add(Int('Iops'))
        self.add(List('OptionGroupMemberships', [
            Str('OptionGroupName'),
            Str('Status'),
        ]))
        self.add(Str('CharacterSetName'))
        self.add(Str('SecondaryAvailabilityZone'))
        self.add(BoolChoice('PubliclyAccessible'))
        self.add(
            List('StatusInfos', [
                Str('StatusType'),
                BoolChoice('Normal'),
                Str('Status'),
                Str('Message'),
            ]))
        self.add(Str('StorageType'))
        self.add(Str('TdeCredentialArn'))
        self.add(Int('DbInstancePort'))
        self.add(Str('DBClusterIdentifier'))
        self.add(BoolChoice('StorageEncrypted'))
        self.add(Str('KmsKeyId'))
        self.add(Str('DbiResourceId'))
        self.add(Str('CACertificateIdentifier'))
        self.add(
            List('DomainMemberships', [
                Str('Domain'),
                Str('Status'),
                Str('FQDN'),
                Str('IAMRoleName'),
            ]))
        self.add(BoolChoice('CopyTagsToSnapshot'))
        self.add(Int('MonitoringInterval'))
        self.add(Str('EnhancedMonitoringResourceArn'))
        self.add(Str('MonitoringRoleArn'))
        self.add(Int('PromotionTier'))
        self.add(Str('DBInstanceArn'))
        self.add(Str('Timezone'))
        self.add(BoolChoice('IAMDatabaseAuthenticationEnabled'))
        self.add(BoolChoice('PerformanceInsightsEnabled'))
        self.add(Str('PerformanceInsightsKMSKeyId'))
        self.add(Int('PerformanceInsightsRetentionPeriod'))
        self.add(Enum('EnabledCloudwatchLogsExports'))
        self.add(List('ProcessorFeatures', [
            Str('Name'),
            Str('Value'),
        ]))
        self.add(BoolChoice('DeletionProtection'))
        self.add(List('AssociatedRoles', [
            Str('RoleArn'),
            Str('FeatureName'),
            Str('Status'),
        ]))
        self.add(List('ListenerEndpoint', [
            Str('Address'),
            Int('Port'),
            Str('HostedZoneId'),
        ]))


#.
#   .--ELB------------------------------------------------------------------


class ELBDescribeLoadBalancersInstanceCreator(InstanceCreator):
    def _fill_instance(self):
        self.add(Str('LoadBalancerName'))
        self.add(Str('DNSName'))
        self.add(Str('CanonicalHostedZoneName'))
        self.add(Str('CanonicalHostedZoneNameID'))
        self.add(
            List('ListenerDescriptions', [
                Dict('Listener', [
                    Str('Protocol'),
                    Int('LoadBalancerPort'),
                    Str('InstanceProtocol'),
                    Int('InstancePort'),
                    Str('SSLCertificateId'),
                ]),
                Enum('PolicyNames'),
            ]))
        self.add(
            Dict('Policies', [
                List('AppCookieStickinessPolicies', [
                    Str('PolicyName'),
                    Str('CookieName'),
                ]),
                List('LBCookieStickinessPolicies', [
                    Str('PolicyName'),
                    Int('CookieExpirationPeriod'),
                ]),
                Enum('OtherPolicies'),
            ]))
        self.add(List('BackendServerDescriptions', [
            Int('InstancePort'),
            Enum('PolicyNames'),
        ]))
        self.add(Enum('AvailabilityZones'))
        self.add(Enum('Subnets'))
        self.add(Int('VPCId'))
        self.add(List('Instances', [
            Str('InstanceId'),
        ]))
        self.add(
            Dict('HealthCheck', [
                Str('Target'),
                Int('Interval'),
                Int('Timeout'),
                Int('UnhealthyThreshold'),
                Int('HealthyThreshold'),
            ]))
        self.add(Dict('SourceSecurityGroup', [
            Str('OwnerAlias'),
            Str('GroupName'),
        ]))
        self.add(Enum('SecurityGroups'))
        self.add(Timestamp('CreatedTime'))
        self.add(Str('Scheme'))
        self.add(List('TagDescriptions', [
            Str('Key'),
            Str('Value'),
        ]))


class ELBDescribeTagsInstanceCreator(InstanceCreator):
    def _fill_instance(self):
        self.add(Str('LoadBalancerName'))
        self.add(List('Tags', [
            Str('Key'),
            Str('Value'),
        ]))


class ELBDescribeInstanceHealthInstanceCreator(InstanceCreator):
    def _fill_instance(self):
        self.add(Str('InstanceId'))
        self.add(Choice('State', ["InService", "OutOfServic", "Unknown"]))
        self.add(Choice('ReasonCode', ["ELB", "Instance", "N/A"]))
        self.add(Str('Description'))


#.
#.
#   .--fake clients--------------------------------------------------------.
#   |           __       _               _ _            _                  |
#   |          / _| __ _| | _____    ___| (_) ___ _ __ | |_ ___            |
#   |         | |_ / _` | |/ / _ \  / __| | |/ _ \ '_ \| __/ __|           |
#   |         |  _| (_| |   <  __/ | (__| | |  __/ | | | |_\__ \           |
#   |         |_|  \__,_|_|\_\___|  \___|_|_|\___|_| |_|\__|___/           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class FakeCloudwatchClient(object):
    def describe_alarms(self, AlarmNames=None):
        alarms = CloudwatchDescribeAlarmsInstanceCreator.create_instances(amount=2)
        if AlarmNames:
            alarms = [alarm for alarm in alarms if alarm['AlarmName'] in AlarmNames]
        return {'MetricAlarms': alarms, 'NextToken': 'string'}

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


#.
