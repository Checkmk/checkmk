#!/usr/bin/env python

import abc
import random
import six

from cmk.special_agents.agent_aws import (
    AWSEC2InstTypes,)

#   .--entities------------------------------------------------------------.
#   |                             _   _ _   _                              |
#   |                   ___ _ __ | |_(_) |_(_) ___  ___                    |
#   |                  / _ \ '_ \| __| | __| |/ _ \/ __|                   |
#   |                 |  __/ | | | |_| | |_| |  __/\__ \                   |
#   |                  \___|_| |_|\__|_|\__|_|\___||___/                   |
#   |                                                                      |
#   '----------------------------------------------------------------------'

#   ---abc------------------------------------------------------------------


class Entity(six.with_metaclass(abc.ABCMeta, object)):
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


class InstanceBuilder(six.with_metaclass(abc.ABCMeta, object)):
    def __init__(self, idx, amount):
        self._idx = idx
        self._amount = amount

    def _fill_instance(self):
        return []

    def create_instance(self):
        instance = {}
        for value in self._fill_instance():
            instance[value.key] = value.create(self._idx, self._amount)
        return instance

    @classmethod
    def create_instances(cls, amount):
        return [cls(idx, amount).create_instance() for idx in xrange(amount)]


#.
#   .--S3-------------------------------------------------------------------


class GlacierListVaultsIB(InstanceBuilder):
    def _fill_instance(self):
        return [
            Str('VaultARN'),
            Str('VaultName'),
            Str('CreationDate'),
            Str('LastInventoryDate'),
            Int('NumberOfArchives'),
            Int('SizeInBytes')
        ]


class GlacierVaultTaggingIB(InstanceBuilder):
    def _fill_instance(self):
        return [
            Str('Key'),
            Str('Value'),
        ]


#.
#   .--S3-------------------------------------------------------------------


class S3ListBucketsIB(InstanceBuilder):
    def _fill_instance(self):
        return [
            Str('Name'),
            Timestamp('CreationDate'),
        ]


class S3BucketTaggingIB(InstanceBuilder):
    def _fill_instance(self):
        return [
            Str('Key'),
            Str('Value'),
        ]


#.
#   .--Cloudwatch-----------------------------------------------------------


class CloudwatchDescribeAlarmsIB(InstanceBuilder):
    def _fill_instance(self):
        return [
            Str('AlarmName'),
            Str('AlarmArn'),
            Str('AlarmDescription'),
            Timestamp('AlarmConfigurationUpdatedTimestamp'),
            BoolChoice('ActionsEnabled'),
            Enum('OKActions'),
            Enum('AlarmActions'),
            Enum('InsufficientDataActions'),
            Choice('StateValue', ['OK', 'ALARM', 'INSUFFICIENT_DATA']),
            Str('StateReason'),
            Str('StateReasonData'),
            Timestamp('StateUpdatedTimestamp'),
            Str('MetricName'),
            Str('Namespace'),
            Choice('Statistic', [
                'SampleCount',
                'Average',
                'Sum',
                'Minimum',
                'Maximum',
            ]),
            Str('ExtendedStatistic'),
            List('Dimensions', [
                Str('Name'),
                Str('Value'),
            ]),
            Int('Period'),
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
            ]),
            Int('EvaluationPeriods'),
            Int('DatapointsToAlarm'),
            Float('Threshold'),
            Choice('ComparisonOperator', [
                'GreaterThanOrEqualToThreshold',
                'GreaterThanThreshold',
                'LessThanThreshold',
                'LessThanOrEqualToThreshold',
            ]),
            Str('TreatMissingData'),
            Str('EvaluateLowSampleCountPercentile'),
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
                    ]),
                ]),
                Str('Expression'),
                Str('Label'),
                BoolChoice('ReturnData'),
            ]),
        ]


#.
#   .--CE-------------------------------------------------------------------


class CEGetCostsAndUsageIB(InstanceBuilder):
    def _fill_instance(self):
        return [
            Dict('TimePeriod', [
                Str('Start'),
                Str('End'),
            ]),
            Dict('Total', [Dict('string', [
                Str('Amount'),
                Str('Unit'),
            ])]),
            List('Groups', [
                Enum('Keys'),
                Dict('Metrics', [Dict('string', [
                    Str('Amount'),
                    Str('Unit'),
                ])]),
            ]),
            BoolChoice('Estimated'),
        ]


#.
#   .--RDS------------------------------------------------------------------


class RDSDescribeAccountAttributesIB(InstanceBuilder):
    def _fill_instance(self):
        return [
            List(
                'AccountQuotas',
                [
                    Int('Used'),
                    Int('Max'),
                ],
                from_choice=Choice('AccountQuotaName', [
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
                ]),
            ),
        ]


class RDSDescribeDBInstancesIB(InstanceBuilder):
    def _fill_instance(self):
        return [
            Str('DBInstanceIdentifier'),
            Str('DBInstanceClass'),
            Str('Engine'),
            Str('DBInstanceStatus'),
            Str('MasterUsername'),
            Str('DBName'),
            Dict('Endpoint', [
                Str('Address'),
                Int('Port'),
                Str('HostedZoneId'),
            ]),
            Int('AllocatedStorage'),
            Timestamp('InstanceCreateTime'),
            Str('PreferredBackupWindow'),
            Int('BackupRetentionPeriod'),
            List('DBSecurityGroups', [
                Str('DBSecurityGroupName'),
                Str('Status'),
            ]),
            List('VpcSecurityGroups', [
                Str('VpcSecurityGroupId'),
                Str('Status'),
            ]),
            List('DBParameterGroups', [
                Str('DBParameterGroupName'),
                Str('ParameterApplyStatus'),
            ]),
            Str('AvailabilityZone'),
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
            ]),
            Str('PreferredMaintenanceWindow'),
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
            ]),
            Timestamp('LatestRestorableTime'),
            BoolChoice('MultiAZ'),
            Str('EngineVersion'),
            BoolChoice('AutoMinorVersionUpgrade'),
            Str('ReadReplicaSourceDBInstanceIdentifier'),
            Enum('ReadReplicaDBInstanceIdentifiers'),
            Enum('ReadReplicaDBClusterIdentifiers'),
            Str('LicenseModel'),
            Int('Iops'),
            List('OptionGroupMemberships', [
                Str('OptionGroupName'),
                Str('Status'),
            ]),
            Str('CharacterSetName'),
            Str('SecondaryAvailabilityZone'),
            BoolChoice('PubliclyAccessible'),
            List('StatusInfos', [
                Str('StatusType'),
                BoolChoice('Normal'),
                Str('Status'),
                Str('Message'),
            ]),
            Str('StorageType'),
            Str('TdeCredentialArn'),
            Int('DbInstancePort'),
            Str('DBClusterIdentifier'),
            BoolChoice('StorageEncrypted'),
            Str('KmsKeyId'),
            Str('DbiResourceId'),
            Str('CACertificateIdentifier'),
            List('DomainMemberships', [
                Str('Domain'),
                Str('Status'),
                Str('FQDN'),
                Str('IAMRoleName'),
            ]),
            BoolChoice('CopyTagsToSnapshot'),
            Int('MonitoringInterval'),
            Str('EnhancedMonitoringResourceArn'),
            Str('MonitoringRoleArn'),
            Int('PromotionTier'),
            Str('DBInstanceArn'),
            Str('Timezone'),
            BoolChoice('IAMDatabaseAuthenticationEnabled'),
            BoolChoice('PerformanceInsightsEnabled'),
            Str('PerformanceInsightsKMSKeyId'),
            Int('PerformanceInsightsRetentionPeriod'),
            Enum('EnabledCloudwatchLogsExports'),
            List('ProcessorFeatures', [
                Str('Name'),
                Str('Value'),
            ]),
            BoolChoice('DeletionProtection'),
            List('AssociatedRoles', [
                Str('RoleArn'),
                Str('FeatureName'),
                Str('Status'),
            ]),
            List('ListenerEndpoint', [
                Str('Address'),
                Int('Port'),
                Str('HostedZoneId'),
            ]),
        ]


#.
#   .--ELB------------------------------------------------------------------


class ELBDescribeLoadBalancersIB(InstanceBuilder):
    def _fill_instance(self):
        return [
            Str('LoadBalancerName'),
            Str('DNSName'),
            Str('CanonicalHostedZoneName'),
            Str('CanonicalHostedZoneNameID'),
            List('ListenerDescriptions', [
                Dict('Listener', [
                    Str('Protocol'),
                    Int('LoadBalancerPort'),
                    Str('InstanceProtocol'),
                    Int('InstancePort'),
                    Str('SSLCertificateId'),
                ]),
                Enum('PolicyNames'),
            ]),
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
            ]),
            List('BackendServerDescriptions', [
                Int('InstancePort'),
                Enum('PolicyNames'),
            ]),
            Enum('AvailabilityZones'),
            Enum('Subnets'),
            Int('VPCId'),
            List('Instances', [
                Str('InstanceId'),
            ]),
            Dict('HealthCheck', [
                Str('Target'),
                Int('Interval'),
                Int('Timeout'),
                Int('UnhealthyThreshold'),
                Int('HealthyThreshold'),
            ]),
            Dict('SourceSecurityGroup', [
                Str('OwnerAlias'),
                Str('GroupName'),
            ]),
            Enum('SecurityGroups'),
            Timestamp('CreatedTime'),
            Str('Scheme'),
            List('TagDescriptions', [
                Str('Key'),
                Str('Value'),
            ]),
        ]


class ELBDescribeTagsIB(InstanceBuilder):
    def _fill_instance(self):
        return [
            Str('LoadBalancerName'),
            List('Tags', [
                Str('Key'),
                Str('Value'),
            ]),
        ]


class ELBDescribeInstanceHealthIB(InstanceBuilder):
    def _fill_instance(self):
        return [
            Str('InstanceId'),
            Choice('State', ["InService", "OutOfService", "Unknown"]),
            Choice('ReasonCode', ["ELB", "Instance", "N/A"]),
            Str('Description'),
        ]


class ELBDescribeAccountLimitsIB(InstanceBuilder):
    def _fill_instance(self):
        return [
            List(
                'Limits',
                [
                    Int('Max'),
                ],
                from_choice=Choice('Name', [
                    "classic-load-balancers",
                    "classic-listeners",
                    "classic-registered-instances",
                ]),
            ),
        ]


#.
#   .--ELBv2----------------------------------------------------------------


class ELBv2DescribeLoadBalancersIB(InstanceBuilder):
    def _fill_instance(self):
        return [
            Str('LoadBalancerArn'),
            Str('DNSName'),
            Str('CanonicalHostedZoneId'),
            Timestamp('CreatedTime'),
            Str('LoadBalancerName'),
            Choice('Scheme', [
                'internet-facing',
                'internal',
            ]),
            Str('VpcId'),
            Dict('State', [
                Choice('Code', [
                    'active',
                    'provisioning',
                    'active_impaired',
                    'failed',
                ]),
                Str('Reason'),
            ]),
            Choice('Type', [
                'application',
                'network',
            ]),
            List('AvailabilityZones', [
                Str('ZoneName'),
                Str('SubnetId'),
                List('LoadBalancerAddresses', [
                    Str('IpAddress'),
                    Str('AllocationId'),
                ]),
            ]),
            Enum('SecurityGroups'),
            Choice('IpAddressType', [
                'ipv4',
                'dualstack',
            ]),
        ]


class ELBv2DescribeTargetGroupsIB(InstanceBuilder):
    def _fill_instance(self):
        return [
            Str('TargetGroupArn'),
            Str('TargetGroupName'),
            Choice('Protocol', [
                'HTTP',
                'HTTPS',
                'TCP',
                'TLS',
            ]),
            Int('Port'),
            Str('VpcId'),
            Choice('HealthCheckProtocol', [
                'HTTP',
                'HTTPS',
                'TCP',
                'TLS',
            ]),
            Str('HealthCheckPort'),
            BoolChoice('HealthCheckEnabled'),
            Int('HealthCheckIntervalSeconds'),
            Int('HealthCheckTimeoutSeconds'),
            Int('HealthyThresholdCount'),
            Int('UnhealthyThresholdCount'),
            Str('HealthCheckPath'),
            Dict('Matcher', [
                Str('HttpCode'),
            ]),
            Enum('LoadBalancerArns'),
            Choice('TargetType', [
                'instance',
                'ip',
                'lambda',
            ]),
        ]


class ELBv2DescribeListenersIB(InstanceBuilder):
    def _fill_instance(self):
        return [
            Str('ListenerArn'),
            Str('LoadBalancerArn'),
            Int('Port'),
            Choice('Protocol', ['HTTP', 'HTTPS', 'TCP', 'TLS']),
            List('Certificates', [
                Str('CertificateArn'),
                BoolChoice('IsDefault'),
            ]),
            Str('SslPolicy'),
            List('DefaultActions', [
                Choice('Type', [
                    'forward',
                    'authenticate-oidc',
                    'authenticate-cognito',
                    'redirect',
                    'fixed-response',
                ]),
                Str('TargetGroupArn'),
                Dict('AuthenticateOidcConfig', [
                    Str('Issuer'),
                    Str('AuthorizationEndpoint'),
                    Str('TokenEndpoint'),
                    Str('UserInfoEndpoint'),
                    Str('ClientId'),
                    Str('ClientSecret'),
                    Str('SessionCookieName'),
                    Str('Scope'),
                    Int('SessionTimeout'),
                    Dict('AuthenticationRequestExtraParams', [
                        Str('string'),
                    ]),
                    Choice('OnUnauthenticatedRequest', [
                        'deny',
                        'allow',
                        'authenticate',
                    ]),
                    BoolChoice('UseExistingClientSecret'),
                ]),
                Dict('AuthenticateCognitoConfig', [
                    Str('UserPoolArn'),
                    Str('UserPoolClientId'),
                    Str('UserPoolDomain'),
                    Str('SessionCookieName'),
                    Str('Scope'),
                    Int('SessionTimeout'),
                    Dict('AuthenticationRequestExtraParams', [
                        Str('string'),
                    ]),
                    Choice('OnUnauthenticatedRequest', [
                        'deny',
                        'allow',
                        'authenticate',
                    ]),
                ]),
                Int('Order'),
                Dict('RedirectConfig', [
                    Str('Protocol'),
                    Str('Port'),
                    Str('Host'),
                    Str('Path'),
                    Str('Query'),
                    Choice('StatusCode', [
                        'HTTP_301',
                        'HTTP_302',
                    ]),
                ]),
                Dict('FixedResponseConfig', [
                    Str('MessageBody'),
                    Str('StatusCode'),
                    Str('ContentType'),
                ]),
            ]),
        ]


class ELBv2DescribeRulesIB(InstanceBuilder):
    def _fill_instance(self):
        return [
            Str('RuleArn'),
            Str('Priority'),
            List('Conditions', [
                Str('Field'),
                Enum('Values'),
                Dict('HostHeaderConfig', [
                    Enum('Values'),
                ]),
                Dict('PathPatternConfig', [
                    Enum('Values'),
                ]),
                Dict('HttpHeaderConfig', [
                    Str('HttpHeaderName'),
                    Enum('Values'),
                ]),
                Dict('QueryStringConfig', [
                    List('Values', [
                        Str('Key'),
                        Str('Value'),
                    ]),
                ]),
                Dict('HttpRequestMethodConfig', [
                    Enum('Values'),
                ]),
                Dict('SourceIpConfig', [
                    Enum('Values'),
                ]),
            ]),
            List('Actions', [
                Choice('Type', [
                    'forward',
                    'authenticate-oidc',
                    'authenticate-cognito',
                    'redirect',
                    'fixed-response',
                ]),
                Str('TargetGroupArn'),
                Dict('AuthenticateOidcConfig', [
                    Str('Issuer'),
                    Str('AuthorizationEndpoint'),
                    Str('TokenEndpoint'),
                    Str('UserInfoEndpoint'),
                    Str('ClientId'),
                    Str('ClientSecret'),
                    Str('SessionCookieName'),
                    Str('Scope'),
                    Int('SessionTimeout'),
                    Dict('AuthenticationRequestExtraParams', [
                        Str('string'),
                    ]),
                    Choice('OnUnauthenticatedRequest', [
                        'deny',
                        'allow',
                        'authenticate',
                    ]),
                    BoolChoice('UseExistingClientSecret'),
                ]),
                Dict('AuthenticateCognitoConfig', [
                    Str('UserPoolArn'),
                    Str('UserPoolClientId'),
                    Str('UserPoolDomain'),
                    Str('SessionCookieName'),
                    Str('Scope'),
                    Int('SessionTimeout'),
                    Dict('AuthenticationRequestExtraParams', [
                        Str('string'),
                    ]),
                    Choice('OnUnauthenticatedRequest', [
                        'deny',
                        'allow',
                        'authenticate',
                    ]),
                ]),
                Str('Order'),
                Dict('RedirectConfig', [
                    Str('Protocol'),
                    Str('Port'),
                    Str('Host'),
                    Str('Path'),
                    Str('Query'),
                    Choice('StatusCode', [
                        'HTTP_301',
                        'HTTP_302',
                    ]),
                ]),
                Dict('FixedResponseConfig', [
                    Str('MessageBody'),
                    Str('StatusCode'),
                    Str('ContentType'),
                ]),
            ]),
            BoolChoice('IsDefault'),
        ]


class ELBv2DescribeAccountLimitsIB(InstanceBuilder):
    def _fill_instance(self):
        return [
            List('Limits', [
                Int('Max'),
            ],
                 from_choice=Choice('Name', [
                     'application-load-balancers',
                     'listeners-per-application-load-balancer',
                     'listeners-per-network-load-balancer',
                     'network-load-balancers',
                     'rules-per-application-load-balancer',
                     'target-groups',
                     'targets-per-application-load-balancer',
                     'targets-per-availability-zone-per-network-load-balancer',
                     'targets-per-network-load-balancer',
                 ])),
        ]


class ELBv2DescribeTargetHealthIB(InstanceBuilder):
    def _fill_instance(self):
        return [
            Dict('Target', [
                Str('Id'),
                Int('Port'),
                Str('AvailabilityZone'),
            ]),
            Str('HealthCheckPort'),
            Dict('TargetHealth', [
                Choice('State', [
                    'initial',
                    'healthy',
                    'unhealthy',
                    'unused',
                    'draining',
                    'unavailable',
                ]),
                Choice('Reason', [
                    'Elb.RegistrationInProgress',
                    'Elb.InitialHealthChecking',
                    'Target.ResponseCodeMismatch',
                    'Target.Timeout',
                    'Target.FailedHealthChecks',
                    'Target.NotRegistered',
                    'Target.NotInUse',
                    'Target.DeregistrationInProgress',
                    'Target.InvalidState',
                    'Target.IpUnusable',
                    'Target.HealthCheckDisabled',
                    'Elb.InternalError',
                ]),
                Str('Description'),
            ]),
        ]


#.
#   .--EC2------------------------------------------------------------------


class EC2DescribeReservedInstancesIB(InstanceBuilder):
    def _fill_instance(self):
        return [
            Str('AvailabilityZone'),
            Int('Duration'),
            Timestamp('End'),
            Str('FixedPrice'),
            Int('InstanceCount'),
            Choice('InstanceType', AWSEC2InstTypes),
            Choice('ProductDescription', [
                'Linux/UNIX',
                'Linux/UNIX (Amazon VPC)',
                'Windows',
                'Windows (Amazon VPC)',
            ]),
            Str('ReservedInstancesId'),
            Timestamp('Start'),
            Choice('State', [
                'payment-pending',
                'active',
                'payment-failed',
                'retired',
            ]),
            Str('UsagePrice'),
            Choice('CurrencyCode', ['USD']),
            Choice('InstanceTenancy', [
                'default',
                'dedicated',
                'host',
            ]),
            Choice('OfferingClass', [
                'standard',
                'convertible',
            ]),
            Choice('OfferingType', [
                'Heavy Utilization',
                'Medium Utilization',
                'Light Utilization',
                'No Upfront',
                'Partial Upfront',
                'All Upfront',
            ]),
            List('RecurringCharges', [
                Float('Amount'),
                Str('Frequency'),
            ]),
            Choice('Scope', [
                'Availability Zone',
                'Region',
            ]),
            List('Tags', [
                Str('Key'),
                Str('Value'),
            ]),
        ]


class EC2DescribeAddressesIB(InstanceBuilder):
    def _fill_instance(self):
        return [
            Str('InstanceId'),
            Str('PublicIp'),
            Str('AllocationId'),
            Str('AssociationId'),
            Choice('Domain', [
                'vpc',
                'standard',
            ]),
            Str('NetworkInterfaceId'),
            Str('NetworkInterfaceOwnerId'),
            Str('PrivateIpAddress'),
            List('Tags', [
                Str('Key'),
                Str('Value'),
            ]),
            Str('PublicIpv4Pool'),
        ]


class EC2DescribeSecurityGroupsIB(InstanceBuilder):
    def _fill_instance(self):
        return [
            Str('Description'),
            Str('GroupName'),
            List('IpPermissions', [
                Int('FromPort'),
                Str('IpProtocol'),
                List('IpRanges', [
                    Str('CidrIp'),
                    Str('Description'),
                ]),
                List('Ipv6Ranges', [
                    Str('CidrIpv6'),
                    Str('Description'),
                ]),
                List('PrefixListIds', [
                    Str('Description'),
                    Str('PrefixListId'),
                ]),
                Int('ToPort'),
                List('UserIdGroupPairs', [
                    Str('Description'),
                    Str('GroupId'),
                    Str('GroupName'),
                    Str('PeeringStatus'),
                    Str('UserId'),
                    Str('VpcId'),
                    Str('VpcPeeringConnectionId'),
                ]),
            ]),
            Str('OwnerId'),
            Str('GroupId'),
            List('IpPermissionsEgress', [
                Int('FromPort'),
                Str('IpProtocol'),
                List('IpRanges', [
                    Str('CidrIp'),
                    Str('Description'),
                ]),
                List('Ipv6Ranges', [
                    Str('CidrIpv6'),
                    Str('Description'),
                ]),
                List('PrefixListIds', [
                    Str('Description'),
                    Str('PrefixListId'),
                ]),
                Int('ToPort'),
                List('UserIdGroupPairs', [
                    Str('Description'),
                    Str('GroupId'),
                    Str('GroupName'),
                    Str('PeeringStatus'),
                    Str('UserId'),
                    Str('VpcId'),
                    Str('VpcPeeringConnectionId'),
                ]),
            ]),
            List('Tags', [
                Str('Key'),
                Str('Value'),
            ]),
            Str('VpcId'),
        ]


class EC2DescribeNetworkInterfacesIB(InstanceBuilder):
    def _fill_instance(self):
        return [
            Dict('Association', [
                Str('AllocationId'),
                Str('AssociationId'),
                Str('IpOwnerId'),
                Str('PublicDnsName'),
                Str('PublicIp'),
            ]),
            Dict('Attachment', [
                Timestamp('AttachTime'),
                Str('AttachmentId'),
                BoolChoice('DeleteOnTermination'),
                Int('DeviceIndex'),
                Str('InstanceId'),
                Str('InstanceOwnerId'),
                Choice('Status', [
                    'attaching',
                    'attached',
                    'detaching',
                    'detached',
                ]),
            ]),
            Str('AvailabilityZone'),
            Str('Description'),
            List('Groups', [
                Str('GroupName'),
                Str('GroupId'),
            ]),
            Choice('InterfaceType', [
                'interface',
                'natGateway',
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
                    Str('AllocationId'),
                    Str('AssociationId'),
                    Str('IpOwnerId'),
                    Str('PublicDnsName'),
                    Str('PublicIp'),
                ]),
                BoolChoice('Primary'),
                Str('PrivateDnsName'),
                Str('PrivateIpAddress'),
            ]),
            Str('RequesterId'),
            BoolChoice('RequesterManaged'),
            BoolChoice('SourceDestCheck'),
            Choice('Status', [
                'available',
                'associated',
                'attaching',
                'in-use',
                'detaching',
            ]),
            Str('SubnetId'),
            List('TagSet', [
                Str('Key'),
                Str('Value'),
            ]),
            Str('VpcId'),
        ]


class EC2DescribeSpotInstanceRequestsIB(InstanceBuilder):
    def _fill_instance(self):
        return [
            Str('ActualBlockHourlyPrice'),
            Str('AvailabilityZoneGroup'),
            Int('BlockDurationMinutes'),
            Timestamp('CreateTime'),
            Dict('Fault', [
                Str('Code'),
                Str('Message'),
            ]),
            Str('InstanceId'),
            Str('LaunchGroup'),
            Dict('LaunchSpecification', [
                Str('UserData'),
                List('SecurityGroups', [
                    Str('GroupName'),
                    Str('GroupId'),
                ]),
                Str('AddressingType'),
                List('BlockDeviceMappings', [
                    Str('DeviceName'),
                    Str('VirtualName'),
                    Dict('Ebs', [
                        BoolChoice('DeleteOnTermination'),
                        Int('Iops'),
                        Str('SnapshotId'),
                        Int('VolumeSize'),
                        Choice('VolumeType', [
                            'standard',
                            'io1',
                            'gp2',
                            'sc1',
                            'st1',
                        ]),
                        BoolChoice('Encrypted'),
                        Str('KmsKeyId'),
                    ]),
                    Str('NoDevice'),
                ]),
                BoolChoice('EbsOptimized'),
                Dict('IamInstanceProfile', [
                    Str('Arn'),
                    Str('Name'),
                ]),
                Str('ImageId'),
                Choice('InstanceType', AWSEC2InstTypes),
                Str('KernelId'),
                Str('KeyName'),
                List('NetworkInterfaces', [
                    BoolChoice('AssociatePublicIpAddress'),
                    BoolChoice('DeleteOnTermination'),
                    Str('Description'),
                    Int('DeviceIndex'),
                    Choice('Groups', ['string']),
                    Int('Ipv6AddressCount'),
                    List('Ipv6Addresses', [
                        Str('Ipv6Address'),
                    ]),
                    Str('NetworkInterfaceId'),
                    Str('PrivateIpAddress'),
                    List('PrivateIpAddresses', [
                        BoolChoice('Primary'),
                        Str('PrivateIpAddress'),
                    ]),
                    Int('SecondaryPrivateIpAddressCount'),
                    Str('SubnetId'),
                ]),
                List('Placement', [
                    Str('AvailabilityZone'),
                    Str('GroupName'),
                    Choice('Tenancy', [
                        'default',
                        'dedicated',
                        'host',
                    ]),
                ]),
                Str('RamdiskId'),
                Str('SubnetId'),
                Dict('Monitoring', [BoolChoice('Enabled')]),
            ]),
            Str('LaunchedAvailabilityZone'),
            Choice('ProductDescription', [
                'Linux/UNIX',
                'Linux/UNIX (Amazon VPC)',
                'Windows',
                'Windows (Amazon VPC)',
            ]),
            Str('SpotInstanceRequestId'),
            Str('SpotPrice'),
            Choice('State', [
                'open',
                'active',
                'closed',
                'cancelled',
                'failed',
            ]),
            Dict('Status', [
                Str('Code'),
                Str('Message'),
                Timestamp('UpdateTime'),
            ]),
            List('Tags', [
                Str('Key'),
                Str('Value'),
            ]),
            Choice('Type', [
                'one-time',
                'persistent',
            ]),
            Timestamp('ValidFrom'),
            Timestamp('ValidUntil'),
            Choice('InstanceInterruptionBehavior', [
                'hibernate',
                'stop',
                'terminate',
            ]),
        ]


class EC2DescribeSpotFleetRequestsIB(InstanceBuilder):
    def _fill_instance(self):
        return [
            Choice('ActivityStatus', [
                'error',
                'pending_fulfillment',
                'pending_termination',
                'fulfilled',
            ]),
            Timestamp('CreateTime'),
            Dict('SpotFleetRequestConfig', [
                Choice('AllocationStrategy', [
                    'lowestPrice',
                    'diversified',
                ]),
                Choice('OnDemandAllocationStrategy', [
                    'lowestPrice',
                    'prioritized',
                ]),
                Str('ClientToken'),
                Choice('ExcessCapacityTerminationPolicy', [
                    'noTermination',
                    'default',
                ]),
                Int('FulfilledCapacity'),
                Int('OnDemandFulfilledCapacity'),
                Str('IamFleetRole'),
                List('LaunchSpecifications', [
                    List('SecurityGroups', [
                        Str('GroupName'),
                        Str('GroupId'),
                    ]),
                    Str('AddressingType'),
                    List('BlockDeviceMappings', [
                        Str('DeviceName'),
                        Str('VirtualName'),
                        Dict('Ebs', [
                            BoolChoice('DeleteOnTermination'),
                            Int('Iops'),
                            Str('SnapshotId'),
                            Int('VolumeSize'),
                            Choice('VolumeType', [
                                'standard',
                                'io1',
                                'gp2',
                                'sc1',
                                'st1',
                            ]),
                            BoolChoice('Encrypted'),
                            Int('KmsKeyId'),
                        ]),
                        Str('NoDevice'),
                    ]),
                    BoolChoice('EbsOptimized'),
                    Dict('IamInstanceProfile', [
                        Str('Arn'),
                        Str('Name'),
                    ]),
                    Str('ImageId'),
                    Choice('InstanceType', AWSEC2InstTypes),
                    Str('KernelId'),
                    Str('KeyName'),
                    Dict('Monitoring', [BoolChoice('Enabled')]),
                    List('NetworkInterfaces', [
                        BoolChoice('AssociatePublicIpAddress'),
                        BoolChoice('DeleteOnTermination'),
                        Str('Description'),
                        Int('DeviceIndex'),
                        Choice('Groups', ['string']),
                        Int('Ipv6AddressCount'),
                        List('Ipv6Addresses', [
                            Str('Ipv6Address'),
                        ]),
                        Str('NetworkInterfaceId'),
                        Str('PrivateIpAddress'),
                        List('PrivateIpAddresses', [
                            BoolChoice('Primary'),
                            Str('PrivateIpAddress'),
                        ]),
                        Int('SecondaryPrivateIpAddressCount'),
                        Str('SubnetId'),
                    ]),
                    List('Placement', [
                        Str('AvailabilityZone'),
                        Str('GroupName'),
                        Choice('Tenancy', [
                            'default',
                            'dedicated',
                            'host',
                        ]),
                    ]),
                    Str('RamdiskId'),
                    Str('SpotPrice'),
                    Str('SubnetId'),
                    Str('UserData'),
                    Float('WeightedCapacity'),
                    List('TagSpecifications', [
                        Choice('ResourceType', [
                            'client-vpn-endpoint',
                            'customer-gateway',
                            'dedicated-host',
                            'dhcp-options',
                            'elastic-ip',
                            'fleet',
                            'fpga-image',
                            'host-reservation',
                            'image',
                            'instance',
                            'internet-gateway',
                            'launch-template',
                            'natgateway',
                            'network-acl',
                            'network-interface',
                            'reserved-instances',
                            'route-table',
                            'security-group',
                            'snapshot',
                            'spot-instances-request',
                            'subnet',
                            'transit-gateway',
                            'transit-gateway-attachment',
                            'transit-gateway-route-table',
                            'volume',
                            'vpc',
                            'vpc-peering-connection',
                            'vpn-connection',
                            'vpn-gateway',
                        ]),
                    ]),
                    List('Tags', [
                        Str('Key'),
                        Str('Value'),
                    ]),
                ]),
                List('LaunchTemplateConfigs', [
                    Dict('LaunchTemplateSpecification', [
                        Str('LaunchTemplateId'),
                        Str('LaunchTemplateName'),
                        Str('Version'),
                    ]),
                    List('Overrides', [
                        Choice('InstanceType', AWSEC2InstTypes),
                        Str('SpotPrice'),
                        Str('SubnetId'),
                        Str('AvailabilityZone'),
                        Float('WeightedCapacity'),
                        Float('Priority'),
                    ]),
                ]),
                Str('SpotPrice'),
                Int('TargetCapacity'),
                Int('OnDemandTargetCapacity'),
                BoolChoice('TerminateInstancesWithExpiration'),
                Choice('Type', [
                    'request',
                    'maintain',
                    'instant',
                ]),
                Timestamp('ValidFrom'),
                Timestamp('ValidUntil'),
                BoolChoice('ReplaceUnhealthyInstances'),
                Choice('InstanceInterruptionBehavior', [
                    'hibernate',
                    'stop',
                    'terminate',
                ]),
                Dict('LoadBalancersConfig', [
                    Dict('ClassicLoadBalancersConfig', [
                        List('ClassicLoadBalancers', [
                            Str('Name'),
                        ]),
                    ]),
                    Dict('TargetGroupsConfig', [
                        List('TargetGroups', [
                            Str('Arn'),
                        ]),
                    ]),
                ]),
                Int('InstancePoolsToUseCount'),
            ]),
            Str('SpotFleetRequestId'),
            Choice('SpotFleetRequestState', [
                'submitted',
                'active',
                'cancelled',
                'failed',
                'cancelled_running',
                'cancelled  _terminating',
                'modifying',
            ]),
        ]


class EC2DescribeInstancesIB(InstanceBuilder):
    def _fill_instance(self):
        return [
            Int('AmiLaunchIndex'),
            Str('ImageId'),
            Str('InstanceId'),
            Choice('InstanceType', AWSEC2InstTypes),
            Str('KernelId'),
            Str('KeyName'),
            Timestamp('LaunchTime'),
            Dict('Monitoring', [
                Choice('State', [
                    'disabled',
                    'disabling',
                    'enabled',
                    'pending',
                ]),
            ]),
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
            ]),
            Str('Platform'),
            Str('PrivateDnsName'),
            Str('PrivateIpAddress'),
            List('ProductCodes', [
                Str('ProductCodeId'),
                Choice('ProductCodeType', [
                    'devpay',
                    'marketplace',
                ]),
            ]),
            Str('PublicDnsName'),
            Str('PublicIpAddress'),
            Str('RamdiskId'),
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
            ]),
            Str('StateTransitionReason'),
            Str('SubnetId'),
            Str('VpcId'),
            Choice('Architecture', [
                'i386',
                'x86_64',
                'arm64',
            ]),
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
            ]),
            Str('ClientToken'),
            BoolChoice('EbsOptimized'),
            BoolChoice('EnaSupport'),
            Choice('Hypervisor', [
                'ovm',
                'xen',
            ]),
            Dict('IamInstanceProfile', [
                Str('Arn'),
                Str('Id'),
            ]),
            Choice('InstanceLifecycle', [
                'spot',
                'scheduled',
            ]),
            List('ElasticGpuAssociations', [
                Str('ElasticGpuId'),
                Str('ElasticGpuAssociationId'),
                Str('ElasticGpuAssociationState'),
                Str('ElasticGpuAssociationTime'),
            ]),
            List('ElasticInferenceAcceleratorAssociations', [
                Str('ElasticInferenceAcceleratorArn'),
                Str('ElasticInferenceAcceleratorAssociationId'),
                Str('ElasticInferenceAcceleratorAssociationState'),
                Timestamp('ElasticInferenceAcceleratorAssociationTime'),
            ]),
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
            ]),
            Str('RootDeviceName'),
            Choice('RootDeviceType', [
                'ebs',
                'instance-store',
            ]),
            List('SecurityGroups', [
                Str('GroupName'),
                Str('GroupId'),
            ]),
            BoolChoice('SourceDestCheck'),
            Str('SpotInstanceRequestId'),
            Str('SriovNetSupport'),
            Dict('StateReason', [
                Str('Code'),
                Str('Message'),
            ]),
            List('Tags', [
                Str('Key'),
                Str('Value'),
            ]),
            Choice('VirtualizationType', [
                'hvm',
                'paravirtual',
            ]),
            Dict('CpuOptions', [
                Int('CoreCount'),
                Int('ThreadsPerCore'),
            ]),
            Str('CapacityReservationId'),
            Dict('CapacityReservationSpecification', [
                Choice('CapacityReservationPreference', [
                    'open',
                    'none',
                ]),
                Dict('CapacityReservationTarget', [
                    Str('CapacityReservationId'),
                ]),
            ]),
            Dict('HibernationOptions', [
                BoolChoice('Configured'),
            ]),
            List('Licenses', [
                Str('LicenseConfigurationArn'),
            ]),
        ]


class EC2DescribeVolumesIB(InstanceBuilder):
    def _fill_instance(self):
        return [
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
            ]),
            Str('AvailabilityZone'),
            Timestamp('CreateTime'),
            BoolChoice('Encrypted'),
            Str('KmsKeyId'),
            Int('Size'),
            Str('SnapshotId'),
            Choice('State', [
                'creating',
                'available',
                'in-use',
                'deleting',
                'deleted',
                'error',
            ]),
            Str('VolumeId'),
            Int('Iops'),
            List('Tags', [
                Str('Key'),
                Str('Value'),
            ]),
            Choice('VolumeType', [
                'standard',
                'io1',
                'gp2',
                'sc1',
                'st1',
            ]),
        ]


class EC2DescribeSnapshotsIB(InstanceBuilder):
    def _fill_instance(self):
        return [
            Str('DataEncryptionKeyId'),
            Str('Description'),
            BoolChoice('Encrypted'),
            Str('KmsKeyId'),
            Str('OwnerId'),
            Str('Progress'),
            Str('SnapshotId'),
            Timestamp('StartTime'),
            Choice('State', [
                'pending',
                'completed',
                'error',
            ]),
            Str('StateMessage'),
            Str('VolumeId'),
            Int('VolumeSize'),
            Str('OwnerAlias'),
            List('Tags', [
                Str('Key'),
                Str('Value'),
            ]),
        ]


class EC2DescribeVolumeStatusIB(InstanceBuilder):
    def _fill_instance(self):
        return [
            List('Actions', [
                Str('Code'),
                Str('Description'),
                Str('EventId'),
                Str('EventType'),
            ]),
            Str('AvailabilityZone'),
            List('Events', [
                Str('Description'),
                Str('EventId'),
                Str('EventType'),
                Timestamp('NotAfter'),
                Timestamp('NotBefore'),
            ]),
            Str('VolumeId'),
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
            ]),
        ]


class EC2DescribeTagsIB(InstanceBuilder):
    def _fill_instance(self):
        return [
            Str('Key'),
            Str('ResourceId'),
            Choice('ResourceType', [
                'client-vpn-endpoint',
                'customer-gateway',
                'dedicated-host',
                'dhcp-options',
                'elastic-ip',
                'fleet',
                'fpga-image',
                'host-reservation',
                'image',
                'instance',
                'internet-gateway',
                'launch-template',
                'natgateway',
                'network-acl',
                'network-interface',
                'reserved-instances',
                'route-table',
                'security-group',
                'snapshot',
                'spot-instances-request',
                'subnet',
                'transit-gateway',
                'transit-gateway-attachment',
                'transit-gateway-route-table',
                'volume',
                'vpc',
                'vpc-peering-connection',
                'vpn-connection',
                'vpn-gateway',
            ]),
            Str('Value'),
        ]


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
        alarms = CloudwatchDescribeAlarmsIB.create_instances(amount=2)
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
