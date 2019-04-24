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
                elem.update({e.key: e.create(choice, amount) for e in self._elements})
                list_.append(elem)
            return list_
        return [{e.key: e.create(x, amount) for e in self._elements} for x in xrange(amount)]


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


class S3ListBucketsIC(InstanceCreator):
    def _fill_instance(self):
        self.add(Str('Name'))
        self.add(Timestamp('CreationDate'))


class S3BucketTaggingIC(InstanceCreator):
    def _fill_instance(self):
        self.add(Str('Key'))
        self.add(Str('Value'))


#.
#   .--Cloudwatch-----------------------------------------------------------


class CloudwatchDescribeAlarmsIC(InstanceCreator):
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


class CEGetCostsAndUsageIC(InstanceCreator):
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


class RDSDescribeAccountAttributesIC(InstanceCreator):
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


class RDSDescribeDBInstancesIC(InstanceCreator):
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


class ELBDescribeLoadBalancersIC(InstanceCreator):
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


class ELBDescribeTagsIC(InstanceCreator):
    def _fill_instance(self):
        self.add(Str('LoadBalancerName'))
        self.add(List('Tags', [
            Str('Key'),
            Str('Value'),
        ]))


class ELBDescribeInstanceHealthIC(InstanceCreator):
    def _fill_instance(self):
        self.add(Str('InstanceId'))
        self.add(Choice('State', ["InService", "OutOfServic", "Unknown"]))
        self.add(Choice('ReasonCode', ["ELB", "Instance", "N/A"]))
        self.add(Str('Description'))


#.
#   .--EC2------------------------------------------------------------------


class EC2DescribeInstancesIC(InstanceCreator):
    def _fill_instance(self):
        self.add(Int('AmiLaunchIndex'))
        self.add(Str('ImageId'))
        self.add(Str('InstanceId'))
        self.add(
            Choice('InstanceType', [
                't1.micro',
                't2.nano',
                't2.micro',
                't2.small',
                't2.medium',
                't2.large',
                't2.xlarge',
                't2.2xlarge',
                't3.nano',
                't3.micro',
                't3.small',
                't3.medium',
                't3.large',
                't3.xlarge',
                't3.2xlarge',
                'm1.small',
                'm1.medium',
                'm1.large',
                'm1.xlarge',
                'm3.medium',
                'm3.large',
                'm3.xlarge',
                'm3.2xlarge',
                'm4.large',
                'm4.xlarge',
                'm4.2xlarge',
                'm4.4xlarge',
                'm4.10xlarge',
                'm4.16xlarge',
                'm2.xlarge',
                'm2.2xlarge',
                'm2.4xlarge',
                'cr1.8xlarge',
                'r3.large',
                'r3.xlarge',
                'r3.2xlarge',
                'r3.4xlarge',
                'r3.8xlarge',
                'r4.large',
                'r4.xlarge',
                'r4.2xlarge',
                'r4.4xlarge',
                'r4.8xlarge',
                'r4.16xlarge',
                'r5.large',
                'r5.xlarge',
                'r5.2xlarge',
                'r5.4xlarge',
                'r5.12xlarge',
                'r5.24xlarge',
                'r5.metal',
                'r5a.large',
                'r5a.xlarge',
                'r5a.2xlarge',
                'r5a.4xlarge',
                'r5a.12xlarge',
                'r5a.24xlarge',
                'r5d.large',
                'r5d.xlarge',
                'r5d.2xlarge',
                'r5d.4xlarge',
                'r5d.12xlarge',
                'r5d.24xlarge',
                'r5d.metal',
                'r5ad.large',
                'r5ad.xlarge',
                'r5ad.2xlarge',
                'r5ad.4xlarge',
                'r5ad.8xlarge',
                'r5ad.12xlarge',
                'r5ad.16xlarge',
                'r5ad.24xlarge',
                'x1.16xlarge',
                'x1.32xlarge',
                'x1e.xlarge',
                'x1e.2xlarge',
                'x1e.4xlarge',
                'x1e.8xlarge',
                'x1e.16xlarge',
                'x1e.32xlarge',
                'i2.xlarge',
                'i2.2xlarge',
                'i2.4xlarge',
                'i2.8xlarge',
                'i3.large',
                'i3.xlarge',
                'i3.2xlarge',
                'i3.4xlarge',
                'i3.8xlarge',
                'i3.16xlarge',
                'i3.metal',
                'hi1.4xlarge',
                'hs1.8xlarge',
                'c1.medium',
                'c1.xlarge',
                'c3.large',
                'c3.xlarge',
                'c3.2xlarge',
                'c3.4xlarge',
                'c3.8xlarge',
                'c4.large',
                'c4.xlarge',
                'c4.2xlarge',
                'c4.4xlarge',
                'c4.8xlarge',
                'c5.large',
                'c5.xlarge',
                'c5.2xlarge',
                'c5.4xlarge',
                'c5.9xlarge',
                'c5.18xlarge',
                'c5d.large',
                'c5d.xlarge',
                'c5d.2xlarge',
                'c5d.4xlarge',
                'c5d.9xlarge',
                'c5d.18xlarge',
                'c5n.large',
                'c5n.xlarge',
                'c5n.2xlarge',
                'c5n.4xlarge',
                'c5n.9xlarge',
                'c5n.18xlarge',
                'cc1.4xlarge',
                'cc2.8xlarge',
                'g2.2xlarge',
                'g2.8xlarge',
                'g3.4xlarge',
                'g3.8xlarge',
                'g3.16xlarge',
                'g3s.xlarge',
                'cg1.4xlarge',
                'p2.xlarge',
                'p2.8xlarge',
                'p2.16xlarge',
                'p3.2xlarge',
                'p3.8xlarge',
                'p3.16xlarge',
                'p3dn.24xlarge',
                'd2.xlarge',
                'd2.2xlarge',
                'd2.4xlarge',
                'd2.8xlarge',
                'f1.2xlarge',
                'f1.4xlarge',
                'f1.16xlarge',
                'm5.large',
                'm5.xlarge',
                'm5.2xlarge',
                'm5.4xlarge',
                'm5.12xlarge',
                'm5.24xlarge',
                'm5.metal',
                'm5a.large',
                'm5a.xlarge',
                'm5a.2xlarge',
                'm5a.4xlarge',
                'm5a.12xlarge',
                'm5a.24xlarge',
                'm5d.large',
                'm5d.xlarge',
                'm5d.2xlarge',
                'm5d.4xlarge',
                'm5d.12xlarge',
                'm5d.24xlarge',
                'm5d.metal',
                'm5ad.large',
                'm5ad.xlarge',
                'm5ad.2xlarge',
                'm5ad.4xlarge',
                'm5ad.8xlarge',
                'm5ad.12xlarge',
                'm5ad.16xlarge',
                'm5ad.24xlarge',
                'h1.2xlarge',
                'h1.4xlarge',
                'h1.8xlarge',
                'h1.16xlarge',
                'z1d.large',
                'z1d.xlarge',
                'z1d.2xlarge',
                'z1d.3xlarge',
                'z1d.6xlarge',
                'z1d.12xlarge',
                'z1d.metal',
                'u-6tb1.metal',
                'u-9tb1.metal',
                'u-12tb1.metal',
                'a1.medium',
                'a1.large',
                'a1.xlarge',
                'a1.2xlarge',
                'a1.4xlarge',
            ]))
        self.add(Str('KernelId'))
        self.add(Str('KeyName'))
        self.add(Timestamp('LaunchTime'))
        self.add(
            Dict('Monitoring', [
                Choice('State', [
                    'disabled',
                    'disabling',
                    'enabled',
                    'pending',
                ]),
            ]))
        self.add(
            Dict('Placement', [
                Str('AvailabilityZone'),
                Str('Affinity'),
                Str('GroupName'),
                Int('PartitionNumber'),
                Str('HostId'),
                Choice('Tenancy', [
                    'default',
                    'dedicated',
                    'host',
                ]),
                Str('SpreadDomain'),
            ]))
        self.add(Str('Platform'))
        self.add(Str('PrivateDnsName'))
        self.add(Str('PrivateIpAddress'))
        self.add(
            List('ProductCodes', [
                Str('ProductCodeId'),
                Choice('ProductCodeType', [
                    'devpay',
                    'marketplace',
                ]),
            ]))
        self.add(Str('PublicDnsName'))
        self.add(Str('PublicIpAddress'))
        self.add(Str('RamdiskId'))
        self.add(
            Dict('State', [
                Int('Code'),
                Choice('Name', [
                    'pending',
                    'running',
                    'shutting-down',
                    'terminated',
                    'stopping',
                    'stopped',
                ]),
            ]))
        self.add(Str('StateTransitionReason'))
        self.add(Str('SubnetId'))
        self.add(Str('VpcId'))
        self.add(Choice('Architecture', [
            'i386',
            'x86_64',
            'arm64',
        ]))
        self.add(
            List('BlockDeviceMappings', [
                Str('DeviceName'),
                Dict('Ebs', [
                    Timestamp('AttachTime'),
                    BoolChoice('DeleteOnTermination'),
                    Choice('Status', [
                        'attaching',
                        'attached',
                        'detaching',
                        'detached',
                    ]),
                    Str('VolumeId'),
                ]),
            ]))
        self.add(Str('ClientToken'))
        self.add(BoolChoice('EbsOptimized'))
        self.add(BoolChoice('EnaSupport'))
        self.add(Choice('Hypervisor', [
            'ovm',
            'xen',
        ]))
        self.add(Dict('IamInstanceProfile', [
            Str('Arn'),
            Str('Id'),
        ]))
        self.add(Choice('InstanceLifecycle', [
            'spot',
            'scheduled',
        ]))
        self.add(
            List('ElasticGpuAssociations', [
                Str('ElasticGpuId'),
                Str('ElasticGpuAssociationId'),
                Str('ElasticGpuAssociationState'),
                Str('ElasticGpuAssociationTime'),
            ]))
        self.add(
            List('ElasticInferenceAcceleratorAssociations', [
                Str('ElasticInferenceAcceleratorArn'),
                Str('ElasticInferenceAcceleratorAssociationId'),
                Str('ElasticInferenceAcceleratorAssociationState'),
                Timestamp('ElasticInferenceAcceleratorAssociationTime'),
            ]))
        self.add(
            List('NetworkInterfaces', [
                Dict('Association', [
                    Str('IpOwnerId'),
                    Str('PublicDnsName'),
                    Str('PublicIp'),
                ]),
                Dict('Attachment', [
                    Timestamp('AttachTime'),
                    Str('AttachmentId'),
                    BoolChoice('DeleteOnTermination'),
                    Int('DeviceIndex'),
                    Choice('Status', [
                        'attaching',
                        'attached',
                        'detaching',
                        'detached',
                    ]),
                ]),
                Str('Description'),
                List('Groups', [
                    Str('GroupName'),
                    Str('GroupId'),
                ]),
                List('Ipv6Addresses', [
                    Str('Ipv6Address'),
                ]),
                Str('MacAddress'),
                Str('NetworkInterfaceId'),
                Str('OwnerId'),
                Str('PrivateDnsName'),
                Str('PrivateIpAddress'),
                List('PrivateIpAddresses', [
                    Dict('Association', [
                        Str('IpOwnerId'),
                        Str('PublicDnsName'),
                        Str('PublicIp'),
                    ]),
                    BoolChoice('Primary'),
                    Str('PrivateDnsName'),
                    Str('PrivateIpAddress'),
                ]),
                BoolChoice('SourceDestCheck'),
                Choice('Status', [
                    'available',
                    'associated',
                    'attaching',
                    'in-use',
                    'detaching',
                ]),
                Str('SubnetId'),
                Str('VpcId'),
            ]))
        self.add(Str('RootDeviceName'))
        self.add(Choice('RootDeviceType', [
            'ebs',
            'instance-store',
        ]))
        self.add(List('SecurityGroups', [
            Str('GroupName'),
            Str('GroupId'),
        ]))
        self.add(BoolChoice('SourceDestCheck'))
        self.add(Str('SpotInstanceRequestId'))
        self.add(Str('SriovNetSupport'))
        self.add(Dict('StateReason', [
            Str('Code'),
            Str('Message'),
        ]))
        self.add(List('Tags', [
            Str('Key'),
            Str('Value'),
        ]))
        self.add(Choice('VirtualizationType', [
            'hvm',
            'paravirtual',
        ]))
        self.add(Dict('CpuOptions', [
            Int('CoreCount'),
            Int('ThreadsPerCore'),
        ]))
        self.add(Str('CapacityReservationId'))
        self.add(
            Dict('CapacityReservationSpecification', [
                Choice('CapacityReservationPreference', [
                    'open',
                    'none',
                ]),
                Dict('CapacityReservationTarget', [
                    Str('CapacityReservationId'),
                ]),
            ]))
        self.add(Dict('HibernationOptions', [
            BoolChoice('Configured'),
        ]))
        self.add(List('Licenses', [
            Str('LicenseConfigurationArn'),
        ]))


class EC2DescribeVolumesIC(InstanceCreator):
    def _fill_instance(self):
        self.add(
            List('Attachments', [
                Timestamp('AttachTime'),
                Str('Device'),
                Str('InstanceId'),
                Choice('State', [
                    'attaching',
                    'attached',
                    'detaching',
                    'detached',
                    'busy',
                ]),
                Str('VolumeId'),
                BoolChoice('DeleteOnTermination'),
            ]))
        self.add(Str('AvailabilityZone'))
        self.add(Timestamp('CreateTime'))
        self.add(BoolChoice('Encrypted'))
        self.add(Str('KmsKeyId'))
        self.add(Int('Size'))
        self.add(Str('SnapshotId'))
        self.add(
            Choice('State', [
                'creating',
                'available',
                'in-use',
                'deleting',
                'deleted',
                'error',
            ]))
        self.add(Str('VolumeId'))
        self.add(Int('Iops'))
        self.add(List('Tags', [
            Str('Key'),
            Str('Value'),
        ]))
        self.add(Choice('VolumeType', [
            'standard',
            'io1',
            'gp2',
            'sc1',
            'st1',
        ]))


class EC2DescribeSnapshotsIC(InstanceCreator):
    def _fill_instance(self):
        self.add(Str('DataEncryptionKeyId'))
        self.add(Str('Description'))
        self.add(BoolChoice('Encrypted'))
        self.add(Str('KmsKeyId'))
        self.add(Str('OwnerId'))
        self.add(Str('Progress'))
        self.add(Str('SnapshotId'))
        self.add(Timestamp('StartTime'))
        self.add(Choice('State', [
            'pending',
            'completed',
            'error',
        ]))
        self.add(Str('StateMessage'))
        self.add(Str('VolumeId'))
        self.add(Int('VolumeSize'))
        self.add(Str('OwnerAlias'))
        self.add(List('Tags', [
            Str('Key'),
            Str('Value'),
        ]))


class EC2DescribeVolumeStatusIC(InstanceCreator):
    def _fill_instance(self):
        self.add(
            List('Actions', [
                Str('Code'),
                Str('Description'),
                Str('EventId'),
                Str('EventType'),
            ]))
        self.add(Str('AvailabilityZone'))
        self.add(
            List('Events', [
                Str('Description'),
                Str('EventId'),
                Str('EventType'),
                Timestamp('NotAfter'),
                Timestamp('NotBefore'),
            ]))
        self.add(Str('VolumeId'))
        self.add(
            Dict('VolumeStatus', [
                List('Details', [
                    Choice('Name', [
                        'io-enabled',
                        'io-performance',
                    ]),
                    Str('Status'),
                ]),
                Choice('Status', [
                    'ok',
                    'impaired',
                    'insufficient-data',
                ]),
            ]))


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
        alarms = CloudwatchDescribeAlarmsIC.create_instances(amount=2)
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
