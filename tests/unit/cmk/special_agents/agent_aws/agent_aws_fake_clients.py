#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import random
from typing import Any, Iterable, Mapping, Optional, Sequence, TypedDict

from cmk.utils.aws_constants import AWSEC2InstTypes

#   .--entities------------------------------------------------------------.
#   |                             _   _ _   _                              |
#   |                   ___ _ __ | |_(_) |_(_) ___  ___                    |
#   |                  / _ \ '_ \| __| | __| |/ _ \/ __|                   |
#   |                 |  __/ | | | |_| | |_| |  __/\__ \                   |
#   |                  \___|_| |_|\__|_|\__|_|\___||___/                   |
#   |                                                                      |
#   '----------------------------------------------------------------------'

#   ---abc------------------------------------------------------------------


class Entity(abc.ABC):
    def __init__(self, key):
        self.key = key

    @abc.abstractmethod
    def create(self, idx, amount):
        return


#   ---structural-----------------------------------------------------------


class List(Entity):
    def __init__(self, key, elements, from_choice=None):
        super().__init__(key)
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
        return [{e.key: e.create(x, amount) for e in self._elements} for x in range(amount)]


class Dict(Entity):
    def __init__(self, key, values, enumerate_keys: Optional[Entity] = None):
        super().__init__(key)
        self._values = values
        self._enumerate_keys = enumerate_keys

    def create(self, idx, amount):
        dict_ = {}
        if self._enumerate_keys:
            for x in range(amount):
                this_idx = "%s-%s" % (self._enumerate_keys.key, x)
                dict_.update({this_idx: self._enumerate_keys.create(this_idx, amount)})
        dict_.update({v.key: v.create(idx, amount) for v in self._values})
        return dict_


#   ---behavioural----------------------------------------------------------


class Str(Entity):
    def __init__(self, key, value=None):
        super().__init__(key)
        self.value = value

    def create(self, idx, amount):
        return "%s-%s" % (self.value or self.key, idx)


class Int(Entity):
    def create(self, idx, amount):
        return random.choice(list(range(100)))


class Float(Entity):
    def create(self, idx, amount):
        return 1.0 * random.choice(list(range(100)))


class Timestamp(Entity):
    def create(self, idx, amount):
        return "2019-%02d-%02d" % (
            random.choice(list(range(1, 13))),
            random.choice(list(range(1, 29))),
        )


class Enum(Entity):
    def create(self, idx, amount):
        return ["%s-%s-%s" % (self.key, idx, x) for x in range(amount)]


class Choice(Entity):
    def __init__(self, key, choices):
        super().__init__(key)
        self.choices = choices

    def create(self, idx, amount):
        return random.choice(self.choices)


class BoolChoice(Choice):
    def __init__(self, key):
        super().__init__(key, [True, False])


class Bytes(Str):
    def create(self, idx, amount):
        return bytes(super().create(idx, amount), "utf-8")


# .
#   .--creators------------------------------------------------------------.
#   |                                    _                                 |
#   |                 ___ _ __ ___  __ _| |_ ___  _ __ ___                 |
#   |                / __| '__/ _ \/ _` | __/ _ \| '__/ __|                |
#   |               | (__| | |  __/ (_| | || (_) | |  \__ \                |
#   |                \___|_|  \___|\__,_|\__\___/|_|  |___/                |
#   |                                                                      |
#   '----------------------------------------------------------------------'

#   .--abc------------------------------------------------------------------


class InstanceBuilder(abc.ABC):
    def __init__(self, idx, amount, skip_entities=None):
        self._idx = idx
        self._amount = amount
        self._skip_entities = [] if not skip_entities else skip_entities

    def _fill_instance(self) -> Iterable[Entity]:
        return []

    def _create_instance(self) -> Mapping[str, Any]:
        return {
            value.key: value.create(self._idx, self._amount)
            for value in self._fill_instance()
            if value.key not in self._skip_entities
        }

    @classmethod
    def create_instances(cls, amount, skip_entities=None):
        return [cls(idx, amount, skip_entities)._create_instance() for idx in range(amount)]


class DictInstanceBuilder(abc.ABC):
    # This class was created in order to support the fake client for AWS Lambda.
    # The Lambda API responses contain dictionaries like:
    # {
    #   'Tags': {
    #   'key': 'value'
    #   }
    # }
    #
    # TODO: Currently complex structures where the value are dictionaries are not yet supported,e.g.
    #
    # class ComplexStructureIB(DictInstanceBuilder):
    #   def _key(self):
    #     return Str('Foo')
    #
    #   def _value(self):
    #     return Dict(Str('Bar'), [Str('Baz')])
    #
    # should return:
    # {
    #   'Foo-0': {
    #     'Bar-0': {"Baz": "Baz"}
    #   }
    # }
    #
    # but the actual output is:
    # {
    #   'Foo-0': {
    #     "Baz": "Baz",
    #   }
    # }

    def __init__(self, idx, amount):
        self._idx = idx
        self._amount = amount

    def _key(self) -> Optional[Entity]:
        return None

    def _value(self) -> Optional[Entity]:
        return None

    @classmethod
    def create_instances(cls, amount) -> Mapping[str, Any]:
        return {
            # static analysis does not recognize that None can not happen because of if clause -> disable warning
            key.create(idx, amount): value.create(idx, amount)
            for idx in range(amount)
            if (
                (key := cls(idx, amount)._key()) is not None
                and (value := cls(idx, amount)._value()) is not None
            )
        }


# .
#   .--S3-------------------------------------------------------------------


class GlacierListVaultsIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            Str("VaultARN"),
            Str("VaultName"),
            Str("CreationDate"),
            Str("LastInventoryDate"),
            Int("NumberOfArchives"),
            Int("SizeInBytes"),
        ]


class GlacierVaultTaggingIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            Str("Key"),
            Str("Value"),
        ]


# .
#   .--S3-------------------------------------------------------------------


class S3ListBucketsIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            Str("Name"),
            Timestamp("CreationDate"),
        ]


class S3BucketTaggingIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            Str("Key"),
            Str("Value"),
        ]


# .
#   .--Cloudwatch-----------------------------------------------------------


class CloudwatchDescribeAlarmsIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            Str("AlarmName"),
            Str("AlarmArn"),
            Str("AlarmDescription"),
            Timestamp("AlarmConfigurationUpdatedTimestamp"),
            BoolChoice("ActionsEnabled"),
            Enum("OKActions"),
            Enum("AlarmActions"),
            Enum("InsufficientDataActions"),
            Choice("StateValue", ["OK", "ALARM", "INSUFFICIENT_DATA"]),
            Str("StateReason"),
            Str("StateReasonData"),
            Timestamp("StateUpdatedTimestamp"),
            Str("MetricName"),
            Str("Namespace"),
            Choice(
                "Statistic",
                [
                    "SampleCount",
                    "Average",
                    "Sum",
                    "Minimum",
                    "Maximum",
                ],
            ),
            Str("ExtendedStatistic"),
            List(
                "Dimensions",
                [
                    Str("Name"),
                    Str("Value"),
                ],
            ),
            Int("Period"),
            Choice(
                "Unit",
                [
                    "Seconds",
                    "Microseconds",
                    "Milliseconds",
                    "Bytes",
                    "Kilobytes",
                    "Megabytes",
                    "Gigabytes",
                    "Terabytes",
                    "Bits",
                    "Kilobits",
                    "Megabits",
                    "Gigabits",
                    "Terabits",
                    "Percent",
                    "Count",
                    "Bytes/Second",
                    "Kilobytes/Second",
                    "Megabytes/Second",
                    "Gigabytes/Second",
                    "Terabytes/Second",
                    "Bits/Second",
                    "Kilobits/Second",
                    "Megabits/Second",
                    "Gigabits/Second",
                    "Terabits/Second",
                    "Count/Second",
                    "None",
                ],
            ),
            Int("EvaluationPeriods"),
            Int("DatapointsToAlarm"),
            Float("Threshold"),
            Choice(
                "ComparisonOperator",
                [
                    "GreaterThanOrEqualToThreshold",
                    "GreaterThanThreshold",
                    "LessThanThreshold",
                    "LessThanOrEqualToThreshold",
                ],
            ),
            Str("TreatMissingData"),
            Str("EvaluateLowSampleCountPercentile"),
            List(
                "Metrics",
                [
                    Str("Id"),
                    Dict(
                        "MetricStat",
                        [
                            Dict(
                                "Metric",
                                [
                                    Str("Namespace"),
                                    Str("MetricName"),
                                    List(
                                        "Dimensions",
                                        [
                                            Str("Name"),
                                            Str("Value"),
                                        ],
                                    ),
                                ],
                            ),
                            Int("Period"),
                            Str("Stat"),
                            Choice(
                                "Unit",
                                [
                                    "Seconds",
                                    "Microseconds",
                                    "Milliseconds",
                                    "Bytes",
                                    "Kilobytes",
                                    "Megabytes",
                                    "Gigabytes",
                                    "Terabytes",
                                    "Bits",
                                    "Kilobits",
                                    "Megabits",
                                    "Gigabits",
                                    "Terabits",
                                    "Percent",
                                    "Count",
                                    "Bytes/Second",
                                    "Kilobytes/Second",
                                    "Megabytes/Second",
                                    "Gigabytes/Second",
                                    "Terabytes/Second",
                                    "Bits/Second",
                                    "Kilobits/Second",
                                    "Megabits/Second",
                                    "Gigabits/Second",
                                    "Terabits/Second",
                                    "Count/Second",
                                    "None",
                                ],
                            ),
                        ],
                    ),
                    Str("Expression"),
                    Str("Label"),
                    BoolChoice("ReturnData"),
                ],
            ),
        ]


# .
#   .--CE-------------------------------------------------------------------


class CEGetCostsAndUsageIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            Dict(
                "TimePeriod",
                [
                    Str("Start"),
                    Str("End"),
                ],
            ),
            Dict(
                "Total",
                [
                    Dict(
                        "string",
                        [
                            Str("Amount"),
                            Str("Unit"),
                        ],
                    )
                ],
            ),
            List(
                "Groups",
                [
                    Enum("Keys"),
                    Dict(
                        "Metrics",
                        [
                            Dict(
                                "string",
                                [
                                    Str("Amount"),
                                    Str("Unit"),
                                ],
                            )
                        ],
                    ),
                ],
            ),
            BoolChoice("Estimated"),
        ]


# .
#   .--RDS------------------------------------------------------------------


class RDSDescribeAccountAttributesIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            List(
                "AccountQuotas",
                [
                    Int("Used"),
                    Int("Max"),
                ],
                from_choice=Choice(
                    "AccountQuotaName",
                    [
                        "DBClusters",
                        "DBClusterParameterGroups",
                        "DBInstances",
                        "EventSubscriptions",
                        "ManualSnapshots",
                        "OptionGroups",
                        "DBParameterGroups",
                        "ReadReplicasPerMaster",
                        "ReservedDBInstances",
                        "DBSecurityGroups",
                        "DBSubnetGroups",
                        "SubnetsPerDBSubnetGroup",
                        "AllocatedStorage",
                        "AuthorizationsPerDBSecurityGroup",
                        "DBClusterRoles",
                    ],
                ),
            ),
        ]


class RDSDescribeDBInstancesIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            Str("DBInstanceIdentifier"),
            Str("DBInstanceClass"),
            Str("Engine"),
            Str("DBInstanceStatus"),
            Str("MasterUsername"),
            Str("DBName"),
            Dict(
                "Endpoint",
                [
                    Str("Address"),
                    Int("Port"),
                    Str("HostedZoneId"),
                ],
            ),
            Int("AllocatedStorage"),
            Timestamp("InstanceCreateTime"),
            Str("PreferredBackupWindow"),
            Int("BackupRetentionPeriod"),
            List(
                "DBSecurityGroups",
                [
                    Str("DBSecurityGroupName"),
                    Str("Status"),
                ],
            ),
            List(
                "VpcSecurityGroups",
                [
                    Str("VpcSecurityGroupId"),
                    Str("Status"),
                ],
            ),
            List(
                "DBParameterGroups",
                [
                    Str("DBParameterGroupName"),
                    Str("ParameterApplyStatus"),
                ],
            ),
            Str("AvailabilityZone"),
            Dict(
                "DBSubnetGroup",
                [
                    Str("DBSubnetGroupName"),
                    Str("DBSubnetGroupDescription"),
                    Str("VpcId"),
                    Str("SubnetGroupStatus"),
                    List(
                        "Subnets",
                        [
                            Str("SubnetIdentifier"),
                            Dict(
                                "SubnetAvailabilityZone",
                                [
                                    Str("Name"),
                                ],
                            ),
                            Str("SubnetStatus"),
                        ],
                    ),
                    Str("DBSubnetGroupArn"),
                ],
            ),
            Str("PreferredMaintenanceWindow"),
            Dict(
                "PendingModifiedValues",
                [
                    Str("DBInstanceClass"),
                    Int("AllocatedStorage"),
                    Str("MasterUserPassword"),
                    Int("Port"),
                    Str("BackupRetentionPeriod"),
                    BoolChoice("MultiAZ"),
                    Str("EngineVersion"),
                    Str("LicenseModel"),
                    Int("Iops"),
                    Str("DBInstanceIdentifier"),
                    Str("StorageType"),
                    Str("CACertificateIdentifier"),
                    Str("DBSubnetGroupName"),
                    Dict(
                        "PendingCloudwatchLogsExports",
                        [
                            Enum("LogTypesToEnable"),
                            Enum("LogTypesToDisable"),
                        ],
                    ),
                    Dict(
                        "ProcessorFeatures",
                        [
                            Str("Name"),
                            Str("Value"),
                        ],
                    ),
                ],
            ),
            Timestamp("LatestRestorableTime"),
            BoolChoice("MultiAZ"),
            Str("EngineVersion"),
            BoolChoice("AutoMinorVersionUpgrade"),
            Str("ReadReplicaSourceDBInstanceIdentifier"),
            Enum("ReadReplicaDBInstanceIdentifiers"),
            Enum("ReadReplicaDBClusterIdentifiers"),
            Str("LicenseModel"),
            Int("Iops"),
            List(
                "OptionGroupMemberships",
                [
                    Str("OptionGroupName"),
                    Str("Status"),
                ],
            ),
            Str("CharacterSetName"),
            Str("SecondaryAvailabilityZone"),
            BoolChoice("PubliclyAccessible"),
            List(
                "StatusInfos",
                [
                    Str("StatusType"),
                    BoolChoice("Normal"),
                    Str("Status"),
                    Str("Message"),
                ],
            ),
            Str("StorageType"),
            Str("TdeCredentialArn"),
            Int("DbInstancePort"),
            Str("DBClusterIdentifier"),
            BoolChoice("StorageEncrypted"),
            Str("KmsKeyId"),
            Str("DbiResourceId"),
            Str("CACertificateIdentifier"),
            List(
                "DomainMemberships",
                [
                    Str("Domain"),
                    Str("Status"),
                    Str("FQDN"),
                    Str("IAMRoleName"),
                ],
            ),
            BoolChoice("CopyTagsToSnapshot"),
            Int("MonitoringInterval"),
            Str("EnhancedMonitoringResourceArn"),
            Str("MonitoringRoleArn"),
            Int("PromotionTier"),
            Str("DBInstanceArn"),
            Str("Timezone"),
            BoolChoice("IAMDatabaseAuthenticationEnabled"),
            BoolChoice("PerformanceInsightsEnabled"),
            Str("PerformanceInsightsKMSKeyId"),
            Int("PerformanceInsightsRetentionPeriod"),
            Enum("EnabledCloudwatchLogsExports"),
            List(
                "ProcessorFeatures",
                [
                    Str("Name"),
                    Str("Value"),
                ],
            ),
            BoolChoice("DeletionProtection"),
            List(
                "AssociatedRoles",
                [
                    Str("RoleArn"),
                    Str("FeatureName"),
                    Str("Status"),
                ],
            ),
            List(
                "ListenerEndpoint",
                [
                    Str("Address"),
                    Int("Port"),
                    Str("HostedZoneId"),
                ],
            ),
        ]


class RDSListTagsForResourceIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [Str("Key"), Str("Value")]


# .
#   .--ELB------------------------------------------------------------------


class ELBDescribeLoadBalancersIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            Str("LoadBalancerName"),
            Str("DNSName"),
            Str("CanonicalHostedZoneName"),
            Str("CanonicalHostedZoneNameID"),
            List(
                "ListenerDescriptions",
                [
                    Dict(
                        "Listener",
                        [
                            Str("Protocol"),
                            Int("LoadBalancerPort"),
                            Str("InstanceProtocol"),
                            Int("InstancePort"),
                            Str("SSLCertificateId"),
                        ],
                    ),
                    Enum("PolicyNames"),
                ],
            ),
            Dict(
                "Policies",
                [
                    List(
                        "AppCookieStickinessPolicies",
                        [
                            Str("PolicyName"),
                            Str("CookieName"),
                        ],
                    ),
                    List(
                        "LBCookieStickinessPolicies",
                        [
                            Str("PolicyName"),
                            Int("CookieExpirationPeriod"),
                        ],
                    ),
                    Enum("OtherPolicies"),
                ],
            ),
            List(
                "BackendServerDescriptions",
                [
                    Int("InstancePort"),
                    Enum("PolicyNames"),
                ],
            ),
            Enum("AvailabilityZones"),
            Enum("Subnets"),
            Int("VPCId"),
            List(
                "Instances",
                [
                    Str("InstanceId"),
                ],
            ),
            Dict(
                "HealthCheck",
                [
                    Str("Target"),
                    Int("Interval"),
                    Int("Timeout"),
                    Int("UnhealthyThreshold"),
                    Int("HealthyThreshold"),
                ],
            ),
            Dict(
                "SourceSecurityGroup",
                [
                    Str("OwnerAlias"),
                    Str("GroupName"),
                ],
            ),
            Enum("SecurityGroups"),
            Timestamp("CreatedTime"),
            Str("Scheme"),
            List(
                "TagDescriptions",
                [
                    Str("Key"),
                    Str("Value"),
                ],
            ),
        ]


class ELBDescribeTagsIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            Str("LoadBalancerName"),
            List(
                "Tags",
                [
                    Str("Key"),
                    Str("Value"),
                ],
            ),
        ]


class ELBDescribeInstanceHealthIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            Str("InstanceId"),
            Choice("State", ["InService", "OutOfService", "Unknown"]),
            Choice("ReasonCode", ["ELB", "Instance", "N/A"]),
            Str("Description"),
        ]


class ELBDescribeAccountLimitsIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            List(
                "Limits",
                [
                    Int("Max"),
                ],
                from_choice=Choice(
                    "Name",
                    [
                        "classic-load-balancers",
                        "classic-listeners",
                        "classic-registered-instances",
                    ],
                ),
            ),
        ]


# .
#   .--ELBv2----------------------------------------------------------------


class ELBv2DescribeLoadBalancersIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            Str("LoadBalancerArn"),
            Str("DNSName"),
            Str("CanonicalHostedZoneId"),
            Timestamp("CreatedTime"),
            Str("LoadBalancerName"),
            Choice(
                "Scheme",
                [
                    "internet-facing",
                    "internal",
                ],
            ),
            Str("VpcId"),
            Dict(
                "State",
                [
                    Choice(
                        "Code",
                        [
                            "active",
                            "provisioning",
                            "active_impaired",
                            "failed",
                        ],
                    ),
                    Str("Reason"),
                ],
            ),
            Choice(
                "Type",
                [
                    "application",
                    "network",
                ],
            ),
            List(
                "AvailabilityZones",
                [
                    Str("ZoneName"),
                    Str("SubnetId"),
                    List(
                        "LoadBalancerAddresses",
                        [
                            Str("IpAddress"),
                            Str("AllocationId"),
                        ],
                    ),
                ],
            ),
            Enum("SecurityGroups"),
            Choice(
                "IpAddressType",
                [
                    "ipv4",
                    "dualstack",
                ],
            ),
        ]


class ELBv2DescribeTargetGroupsIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            Str("TargetGroupArn"),
            Str("TargetGroupName"),
            Choice(
                "Protocol",
                [
                    "HTTP",
                    "HTTPS",
                    "TCP",
                    "TLS",
                ],
            ),
            Int("Port"),
            Str("VpcId"),
            Choice(
                "HealthCheckProtocol",
                [
                    "HTTP",
                    "HTTPS",
                    "TCP",
                    "TLS",
                ],
            ),
            Str("HealthCheckPort"),
            BoolChoice("HealthCheckEnabled"),
            Int("HealthCheckIntervalSeconds"),
            Int("HealthCheckTimeoutSeconds"),
            Int("HealthyThresholdCount"),
            Int("UnhealthyThresholdCount"),
            Str("HealthCheckPath"),
            Dict(
                "Matcher",
                [
                    Str("HttpCode"),
                ],
            ),
            Enum("LoadBalancerArns"),
            Choice(
                "TargetType",
                [
                    "instance",
                    "ip",
                    "lambda",
                ],
            ),
        ]


class ELBv2DescribeListenersIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            Str("ListenerArn"),
            Str("LoadBalancerArn"),
            Int("Port"),
            Choice("Protocol", ["HTTP", "HTTPS", "TCP", "TLS"]),
            List(
                "Certificates",
                [
                    Str("CertificateArn"),
                    BoolChoice("IsDefault"),
                ],
            ),
            Str("SslPolicy"),
            List(
                "DefaultActions",
                [
                    Choice(
                        "Type",
                        [
                            "forward",
                            "authenticate-oidc",
                            "authenticate-cognito",
                            "redirect",
                            "fixed-response",
                        ],
                    ),
                    Str("TargetGroupArn"),
                    Dict(
                        "AuthenticateOidcConfig",
                        [
                            Str("Issuer"),
                            Str("AuthorizationEndpoint"),
                            Str("TokenEndpoint"),
                            Str("UserInfoEndpoint"),
                            Str("ClientId"),
                            Str("ClientSecret"),
                            Str("SessionCookieName"),
                            Str("Scope"),
                            Int("SessionTimeout"),
                            Dict(
                                "AuthenticationRequestExtraParams",
                                [
                                    Str("string"),
                                ],
                            ),
                            Choice(
                                "OnUnauthenticatedRequest",
                                [
                                    "deny",
                                    "allow",
                                    "authenticate",
                                ],
                            ),
                            BoolChoice("UseExistingClientSecret"),
                        ],
                    ),
                    Dict(
                        "AuthenticateCognitoConfig",
                        [
                            Str("UserPoolArn"),
                            Str("UserPoolClientId"),
                            Str("UserPoolDomain"),
                            Str("SessionCookieName"),
                            Str("Scope"),
                            Int("SessionTimeout"),
                            Dict(
                                "AuthenticationRequestExtraParams",
                                [
                                    Str("string"),
                                ],
                            ),
                            Choice(
                                "OnUnauthenticatedRequest",
                                [
                                    "deny",
                                    "allow",
                                    "authenticate",
                                ],
                            ),
                        ],
                    ),
                    Int("Order"),
                    Dict(
                        "RedirectConfig",
                        [
                            Str("Protocol"),
                            Str("Port"),
                            Str("Host"),
                            Str("Path"),
                            Str("Query"),
                            Choice(
                                "StatusCode",
                                [
                                    "HTTP_301",
                                    "HTTP_302",
                                ],
                            ),
                        ],
                    ),
                    Dict(
                        "FixedResponseConfig",
                        [
                            Str("MessageBody"),
                            Str("StatusCode"),
                            Str("ContentType"),
                        ],
                    ),
                ],
            ),
        ]


class ELBv2DescribeRulesIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            Str("RuleArn"),
            Str("Priority"),
            List(
                "Conditions",
                [
                    Str("Field"),
                    Enum("Values"),
                    Dict(
                        "HostHeaderConfig",
                        [
                            Enum("Values"),
                        ],
                    ),
                    Dict(
                        "PathPatternConfig",
                        [
                            Enum("Values"),
                        ],
                    ),
                    Dict(
                        "HttpHeaderConfig",
                        [
                            Str("HttpHeaderName"),
                            Enum("Values"),
                        ],
                    ),
                    Dict(
                        "QueryStringConfig",
                        [
                            List(
                                "Values",
                                [
                                    Str("Key"),
                                    Str("Value"),
                                ],
                            ),
                        ],
                    ),
                    Dict(
                        "HttpRequestMethodConfig",
                        [
                            Enum("Values"),
                        ],
                    ),
                    Dict(
                        "SourceIpConfig",
                        [
                            Enum("Values"),
                        ],
                    ),
                ],
            ),
            List(
                "Actions",
                [
                    Choice(
                        "Type",
                        [
                            "forward",
                            "authenticate-oidc",
                            "authenticate-cognito",
                            "redirect",
                            "fixed-response",
                        ],
                    ),
                    Str("TargetGroupArn"),
                    Dict(
                        "AuthenticateOidcConfig",
                        [
                            Str("Issuer"),
                            Str("AuthorizationEndpoint"),
                            Str("TokenEndpoint"),
                            Str("UserInfoEndpoint"),
                            Str("ClientId"),
                            Str("ClientSecret"),
                            Str("SessionCookieName"),
                            Str("Scope"),
                            Int("SessionTimeout"),
                            Dict(
                                "AuthenticationRequestExtraParams",
                                [
                                    Str("string"),
                                ],
                            ),
                            Choice(
                                "OnUnauthenticatedRequest",
                                [
                                    "deny",
                                    "allow",
                                    "authenticate",
                                ],
                            ),
                            BoolChoice("UseExistingClientSecret"),
                        ],
                    ),
                    Dict(
                        "AuthenticateCognitoConfig",
                        [
                            Str("UserPoolArn"),
                            Str("UserPoolClientId"),
                            Str("UserPoolDomain"),
                            Str("SessionCookieName"),
                            Str("Scope"),
                            Int("SessionTimeout"),
                            Dict(
                                "AuthenticationRequestExtraParams",
                                [
                                    Str("string"),
                                ],
                            ),
                            Choice(
                                "OnUnauthenticatedRequest",
                                [
                                    "deny",
                                    "allow",
                                    "authenticate",
                                ],
                            ),
                        ],
                    ),
                    Str("Order"),
                    Dict(
                        "RedirectConfig",
                        [
                            Str("Protocol"),
                            Str("Port"),
                            Str("Host"),
                            Str("Path"),
                            Str("Query"),
                            Choice(
                                "StatusCode",
                                [
                                    "HTTP_301",
                                    "HTTP_302",
                                ],
                            ),
                        ],
                    ),
                    Dict(
                        "FixedResponseConfig",
                        [
                            Str("MessageBody"),
                            Str("StatusCode"),
                            Str("ContentType"),
                        ],
                    ),
                ],
            ),
            BoolChoice("IsDefault"),
        ]


class ELBv2DescribeAccountLimitsIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            List(
                "Limits",
                [
                    Int("Max"),
                ],
                from_choice=Choice(
                    "Name",
                    [
                        "application-load-balancers",
                        "listeners-per-application-load-balancer",
                        "listeners-per-network-load-balancer",
                        "network-load-balancers",
                        "rules-per-application-load-balancer",
                        "target-groups",
                        "targets-per-application-load-balancer",
                        "targets-per-availability-zone-per-network-load-balancer",
                        "targets-per-network-load-balancer",
                    ],
                ),
            ),
        ]


class ELBv2DescribeTargetHealthIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            Dict(
                "Target",
                [
                    Str("Id"),
                    Int("Port"),
                    Str("AvailabilityZone"),
                ],
            ),
            Str("HealthCheckPort"),
            Dict(
                "TargetHealth",
                [
                    Choice(
                        "State",
                        [
                            "initial",
                            "healthy",
                            "unhealthy",
                            "unused",
                            "draining",
                            "unavailable",
                        ],
                    ),
                    Choice(
                        "Reason",
                        [
                            "Elb.RegistrationInProgress",
                            "Elb.InitialHealthChecking",
                            "Target.ResponseCodeMismatch",
                            "Target.Timeout",
                            "Target.FailedHealthChecks",
                            "Target.NotRegistered",
                            "Target.NotInUse",
                            "Target.DeregistrationInProgress",
                            "Target.InvalidState",
                            "Target.IpUnusable",
                            "Target.HealthCheckDisabled",
                            "Elb.InternalError",
                        ],
                    ),
                    Str("Description"),
                ],
            ),
        ]


# .
#   .--EC2------------------------------------------------------------------


class EC2DescribeReservedInstancesIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            Str("AvailabilityZone"),
            Int("Duration"),
            Timestamp("End"),
            Str("FixedPrice"),
            Int("InstanceCount"),
            Choice("InstanceType", AWSEC2InstTypes),
            Choice(
                "ProductDescription",
                [
                    "Linux/UNIX",
                    "Linux/UNIX (Amazon VPC)",
                    "Windows",
                    "Windows (Amazon VPC)",
                ],
            ),
            Str("ReservedInstancesId"),
            Timestamp("Start"),
            Choice(
                "State",
                [
                    "payment-pending",
                    "active",
                    "payment-failed",
                    "retired",
                ],
            ),
            Str("UsagePrice"),
            Choice("CurrencyCode", ["USD"]),
            Choice(
                "InstanceTenancy",
                [
                    "default",
                    "dedicated",
                    "host",
                ],
            ),
            Choice(
                "OfferingClass",
                [
                    "standard",
                    "convertible",
                ],
            ),
            Choice(
                "OfferingType",
                [
                    "Heavy Utilization",
                    "Medium Utilization",
                    "Light Utilization",
                    "No Upfront",
                    "Partial Upfront",
                    "All Upfront",
                ],
            ),
            List(
                "RecurringCharges",
                [
                    Float("Amount"),
                    Str("Frequency"),
                ],
            ),
            Choice(
                "Scope",
                [
                    "Availability Zone",
                    "Region",
                ],
            ),
            List(
                "Tags",
                [
                    Str("Key"),
                    Str("Value"),
                ],
            ),
        ]


class EC2DescribeAddressesIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            Str("InstanceId"),
            Str("PublicIp"),
            Str("AllocationId"),
            Str("AssociationId"),
            Choice(
                "Domain",
                [
                    "vpc",
                    "standard",
                ],
            ),
            Str("NetworkInterfaceId"),
            Str("NetworkInterfaceOwnerId"),
            Str("PrivateIpAddress"),
            List(
                "Tags",
                [
                    Str("Key"),
                    Str("Value"),
                ],
            ),
            Str("PublicIpv4Pool"),
        ]


class EC2DescribeSecurityGroupsIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            Str("Description"),
            Str("GroupName"),
            List(
                "IpPermissions",
                [
                    Int("FromPort"),
                    Str("IpProtocol"),
                    List(
                        "IpRanges",
                        [
                            Str("CidrIp"),
                            Str("Description"),
                        ],
                    ),
                    List(
                        "Ipv6Ranges",
                        [
                            Str("CidrIpv6"),
                            Str("Description"),
                        ],
                    ),
                    List(
                        "PrefixListIds",
                        [
                            Str("Description"),
                            Str("PrefixListId"),
                        ],
                    ),
                    Int("ToPort"),
                    List(
                        "UserIdGroupPairs",
                        [
                            Str("Description"),
                            Str("GroupId"),
                            Str("GroupName"),
                            Str("PeeringStatus"),
                            Str("UserId"),
                            Str("VpcId"),
                            Str("VpcPeeringConnectionId"),
                        ],
                    ),
                ],
            ),
            Str("OwnerId"),
            Str("GroupId"),
            List(
                "IpPermissionsEgress",
                [
                    Int("FromPort"),
                    Str("IpProtocol"),
                    List(
                        "IpRanges",
                        [
                            Str("CidrIp"),
                            Str("Description"),
                        ],
                    ),
                    List(
                        "Ipv6Ranges",
                        [
                            Str("CidrIpv6"),
                            Str("Description"),
                        ],
                    ),
                    List(
                        "PrefixListIds",
                        [
                            Str("Description"),
                            Str("PrefixListId"),
                        ],
                    ),
                    Int("ToPort"),
                    List(
                        "UserIdGroupPairs",
                        [
                            Str("Description"),
                            Str("GroupId"),
                            Str("GroupName"),
                            Str("PeeringStatus"),
                            Str("UserId"),
                            Str("VpcId"),
                            Str("VpcPeeringConnectionId"),
                        ],
                    ),
                ],
            ),
            List(
                "Tags",
                [
                    Str("Key"),
                    Str("Value"),
                ],
            ),
            Str("VpcId"),
        ]


class EC2DescribeNetworkInterfacesIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            Dict(
                "Association",
                [
                    Str("AllocationId"),
                    Str("AssociationId"),
                    Str("IpOwnerId"),
                    Str("PublicDnsName"),
                    Str("PublicIp"),
                ],
            ),
            Dict(
                "Attachment",
                [
                    Timestamp("AttachTime"),
                    Str("AttachmentId"),
                    BoolChoice("DeleteOnTermination"),
                    Int("DeviceIndex"),
                    Str("InstanceId"),
                    Str("InstanceOwnerId"),
                    Choice(
                        "Status",
                        [
                            "attaching",
                            "attached",
                            "detaching",
                            "detached",
                        ],
                    ),
                ],
            ),
            Str("AvailabilityZone"),
            Str("Description"),
            List(
                "Groups",
                [
                    Str("GroupName"),
                    Str("GroupId"),
                ],
            ),
            Choice(
                "InterfaceType",
                [
                    "interface",
                    "natGateway",
                ],
            ),
            List(
                "Ipv6Addresses",
                [
                    Str("Ipv6Address"),
                ],
            ),
            Str("MacAddress"),
            Str("NetworkInterfaceId"),
            Str("OwnerId"),
            Str("PrivateDnsName"),
            Str("PrivateIpAddress"),
            List(
                "PrivateIpAddresses",
                [
                    Dict(
                        "Association",
                        [
                            Str("AllocationId"),
                            Str("AssociationId"),
                            Str("IpOwnerId"),
                            Str("PublicDnsName"),
                            Str("PublicIp"),
                        ],
                    ),
                    BoolChoice("Primary"),
                    Str("PrivateDnsName"),
                    Str("PrivateIpAddress"),
                ],
            ),
            Str("RequesterId"),
            BoolChoice("RequesterManaged"),
            BoolChoice("SourceDestCheck"),
            Choice(
                "Status",
                [
                    "available",
                    "associated",
                    "attaching",
                    "in-use",
                    "detaching",
                ],
            ),
            Str("SubnetId"),
            List(
                "TagSet",
                [
                    Str("Key"),
                    Str("Value"),
                ],
            ),
            Str("VpcId"),
        ]


class EC2DescribeSpotInstanceRequestsIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            Str("ActualBlockHourlyPrice"),
            Str("AvailabilityZoneGroup"),
            Int("BlockDurationMinutes"),
            Timestamp("CreateTime"),
            Dict(
                "Fault",
                [
                    Str("Code"),
                    Str("Message"),
                ],
            ),
            Str("InstanceId"),
            Str("LaunchGroup"),
            Dict(
                "LaunchSpecification",
                [
                    Str("UserData"),
                    List(
                        "SecurityGroups",
                        [
                            Str("GroupName"),
                            Str("GroupId"),
                        ],
                    ),
                    Str("AddressingType"),
                    List(
                        "BlockDeviceMappings",
                        [
                            Str("DeviceName"),
                            Str("VirtualName"),
                            Dict(
                                "Ebs",
                                [
                                    BoolChoice("DeleteOnTermination"),
                                    Int("Iops"),
                                    Str("SnapshotId"),
                                    Int("VolumeSize"),
                                    Choice(
                                        "VolumeType",
                                        [
                                            "standard",
                                            "io1",
                                            "gp2",
                                            "sc1",
                                            "st1",
                                        ],
                                    ),
                                    BoolChoice("Encrypted"),
                                    Str("KmsKeyId"),
                                ],
                            ),
                            Str("NoDevice"),
                        ],
                    ),
                    BoolChoice("EbsOptimized"),
                    Dict(
                        "IamInstanceProfile",
                        [
                            Str("Arn"),
                            Str("Name"),
                        ],
                    ),
                    Str("ImageId"),
                    Choice("InstanceType", AWSEC2InstTypes),
                    Str("KernelId"),
                    Str("KeyName"),
                    List(
                        "NetworkInterfaces",
                        [
                            BoolChoice("AssociatePublicIpAddress"),
                            BoolChoice("DeleteOnTermination"),
                            Str("Description"),
                            Int("DeviceIndex"),
                            Choice("Groups", ["string"]),
                            Int("Ipv6AddressCount"),
                            List(
                                "Ipv6Addresses",
                                [
                                    Str("Ipv6Address"),
                                ],
                            ),
                            Str("NetworkInterfaceId"),
                            Str("PrivateIpAddress"),
                            List(
                                "PrivateIpAddresses",
                                [
                                    BoolChoice("Primary"),
                                    Str("PrivateIpAddress"),
                                ],
                            ),
                            Int("SecondaryPrivateIpAddressCount"),
                            Str("SubnetId"),
                        ],
                    ),
                    List(
                        "Placement",
                        [
                            Str("AvailabilityZone"),
                            Str("GroupName"),
                            Choice(
                                "Tenancy",
                                [
                                    "default",
                                    "dedicated",
                                    "host",
                                ],
                            ),
                        ],
                    ),
                    Str("RamdiskId"),
                    Str("SubnetId"),
                    Dict("Monitoring", [BoolChoice("Enabled")]),
                ],
            ),
            Str("LaunchedAvailabilityZone"),
            Choice(
                "ProductDescription",
                [
                    "Linux/UNIX",
                    "Linux/UNIX (Amazon VPC)",
                    "Windows",
                    "Windows (Amazon VPC)",
                ],
            ),
            Str("SpotInstanceRequestId"),
            Str("SpotPrice"),
            Choice(
                "State",
                [
                    "open",
                    "active",
                    "closed",
                    "cancelled",
                    "failed",
                ],
            ),
            Dict(
                "Status",
                [
                    Str("Code"),
                    Str("Message"),
                    Timestamp("UpdateTime"),
                ],
            ),
            List(
                "Tags",
                [
                    Str("Key"),
                    Str("Value"),
                ],
            ),
            Choice(
                "Type",
                [
                    "one-time",
                    "persistent",
                ],
            ),
            Timestamp("ValidFrom"),
            Timestamp("ValidUntil"),
            Choice(
                "InstanceInterruptionBehavior",
                [
                    "hibernate",
                    "stop",
                    "terminate",
                ],
            ),
        ]


class EC2DescribeSpotFleetRequestsIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            Choice(
                "ActivityStatus",
                [
                    "error",
                    "pending_fulfillment",
                    "pending_termination",
                    "fulfilled",
                ],
            ),
            Timestamp("CreateTime"),
            Dict(
                "SpotFleetRequestConfig",
                [
                    Choice(
                        "AllocationStrategy",
                        [
                            "lowestPrice",
                            "diversified",
                        ],
                    ),
                    Choice(
                        "OnDemandAllocationStrategy",
                        [
                            "lowestPrice",
                            "prioritized",
                        ],
                    ),
                    Str("ClientToken"),
                    Choice(
                        "ExcessCapacityTerminationPolicy",
                        [
                            "noTermination",
                            "default",
                        ],
                    ),
                    Int("FulfilledCapacity"),
                    Int("OnDemandFulfilledCapacity"),
                    Str("IamFleetRole"),
                    List(
                        "LaunchSpecifications",
                        [
                            List(
                                "SecurityGroups",
                                [
                                    Str("GroupName"),
                                    Str("GroupId"),
                                ],
                            ),
                            Str("AddressingType"),
                            List(
                                "BlockDeviceMappings",
                                [
                                    Str("DeviceName"),
                                    Str("VirtualName"),
                                    Dict(
                                        "Ebs",
                                        [
                                            BoolChoice("DeleteOnTermination"),
                                            Int("Iops"),
                                            Str("SnapshotId"),
                                            Int("VolumeSize"),
                                            Choice(
                                                "VolumeType",
                                                [
                                                    "standard",
                                                    "io1",
                                                    "gp2",
                                                    "sc1",
                                                    "st1",
                                                ],
                                            ),
                                            BoolChoice("Encrypted"),
                                            Int("KmsKeyId"),
                                        ],
                                    ),
                                    Str("NoDevice"),
                                ],
                            ),
                            BoolChoice("EbsOptimized"),
                            Dict(
                                "IamInstanceProfile",
                                [
                                    Str("Arn"),
                                    Str("Name"),
                                ],
                            ),
                            Str("ImageId"),
                            Choice("InstanceType", AWSEC2InstTypes),
                            Str("KernelId"),
                            Str("KeyName"),
                            Dict("Monitoring", [BoolChoice("Enabled")]),
                            List(
                                "NetworkInterfaces",
                                [
                                    BoolChoice("AssociatePublicIpAddress"),
                                    BoolChoice("DeleteOnTermination"),
                                    Str("Description"),
                                    Int("DeviceIndex"),
                                    Choice("Groups", ["string"]),
                                    Int("Ipv6AddressCount"),
                                    List(
                                        "Ipv6Addresses",
                                        [
                                            Str("Ipv6Address"),
                                        ],
                                    ),
                                    Str("NetworkInterfaceId"),
                                    Str("PrivateIpAddress"),
                                    List(
                                        "PrivateIpAddresses",
                                        [
                                            BoolChoice("Primary"),
                                            Str("PrivateIpAddress"),
                                        ],
                                    ),
                                    Int("SecondaryPrivateIpAddressCount"),
                                    Str("SubnetId"),
                                ],
                            ),
                            List(
                                "Placement",
                                [
                                    Str("AvailabilityZone"),
                                    Str("GroupName"),
                                    Choice(
                                        "Tenancy",
                                        [
                                            "default",
                                            "dedicated",
                                            "host",
                                        ],
                                    ),
                                ],
                            ),
                            Str("RamdiskId"),
                            Str("SpotPrice"),
                            Str("SubnetId"),
                            Str("UserData"),
                            Float("WeightedCapacity"),
                            List(
                                "TagSpecifications",
                                [
                                    Choice(
                                        "ResourceType",
                                        [
                                            "client-vpn-endpoint",
                                            "customer-gateway",
                                            "dedicated-host",
                                            "dhcp-options",
                                            "elastic-ip",
                                            "fleet",
                                            "fpga-image",
                                            "host-reservation",
                                            "image",
                                            "instance",
                                            "internet-gateway",
                                            "launch-template",
                                            "natgateway",
                                            "network-acl",
                                            "network-interface",
                                            "reserved-instances",
                                            "route-table",
                                            "security-group",
                                            "snapshot",
                                            "spot-instances-request",
                                            "subnet",
                                            "transit-gateway",
                                            "transit-gateway-attachment",
                                            "transit-gateway-route-table",
                                            "volume",
                                            "vpc",
                                            "vpc-peering-connection",
                                            "vpn-connection",
                                            "vpn-gateway",
                                        ],
                                    ),
                                ],
                            ),
                            List(
                                "Tags",
                                [
                                    Str("Key"),
                                    Str("Value"),
                                ],
                            ),
                        ],
                    ),
                    List(
                        "LaunchTemplateConfigs",
                        [
                            Dict(
                                "LaunchTemplateSpecification",
                                [
                                    Str("LaunchTemplateId"),
                                    Str("LaunchTemplateName"),
                                    Str("Version"),
                                ],
                            ),
                            List(
                                "Overrides",
                                [
                                    Choice("InstanceType", AWSEC2InstTypes),
                                    Str("SpotPrice"),
                                    Str("SubnetId"),
                                    Str("AvailabilityZone"),
                                    Float("WeightedCapacity"),
                                    Float("Priority"),
                                ],
                            ),
                        ],
                    ),
                    Str("SpotPrice"),
                    Int("TargetCapacity"),
                    Int("OnDemandTargetCapacity"),
                    BoolChoice("TerminateInstancesWithExpiration"),
                    Choice(
                        "Type",
                        [
                            "request",
                            "maintain",
                            "instant",
                        ],
                    ),
                    Timestamp("ValidFrom"),
                    Timestamp("ValidUntil"),
                    BoolChoice("ReplaceUnhealthyInstances"),
                    Choice(
                        "InstanceInterruptionBehavior",
                        [
                            "hibernate",
                            "stop",
                            "terminate",
                        ],
                    ),
                    Dict(
                        "LoadBalancersConfig",
                        [
                            Dict(
                                "ClassicLoadBalancersConfig",
                                [
                                    List(
                                        "ClassicLoadBalancers",
                                        [
                                            Str("Name"),
                                        ],
                                    ),
                                ],
                            ),
                            Dict(
                                "TargetGroupsConfig",
                                [
                                    List(
                                        "TargetGroups",
                                        [
                                            Str("Arn"),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                    Int("InstancePoolsToUseCount"),
                ],
            ),
            Str("SpotFleetRequestId"),
            Choice(
                "SpotFleetRequestState",
                [
                    "submitted",
                    "active",
                    "cancelled",
                    "failed",
                    "cancelled_running",
                    "cancelled  _terminating",
                    "modifying",
                ],
            ),
        ]


class EC2DescribeInstancesIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            Int("AmiLaunchIndex"),
            Str("ImageId"),
            Str("InstanceId"),
            Choice("InstanceType", AWSEC2InstTypes),
            Str("KernelId"),
            Str("KeyName"),
            Timestamp("LaunchTime"),
            Dict(
                "Monitoring",
                [
                    Choice(
                        "State",
                        [
                            "disabled",
                            "disabling",
                            "enabled",
                            "pending",
                        ],
                    ),
                ],
            ),
            Dict(
                "Placement",
                [
                    Str("AvailabilityZone"),
                    Str("Affinity"),
                    Str("GroupName"),
                    Int("PartitionNumber"),
                    Str("HostId"),
                    Choice(
                        "Tenancy",
                        [
                            "default",
                            "dedicated",
                            "host",
                        ],
                    ),
                    Str("SpreadDomain"),
                ],
            ),
            Str("Platform"),
            Str("PrivateDnsName"),
            Str("PrivateIpAddress"),
            List(
                "ProductCodes",
                [
                    Str("ProductCodeId"),
                    Choice(
                        "ProductCodeType",
                        [
                            "devpay",
                            "marketplace",
                        ],
                    ),
                ],
            ),
            Str("PublicDnsName"),
            Str("PublicIpAddress"),
            Str("RamdiskId"),
            Dict(
                "State",
                [
                    Int("Code"),
                    Choice(
                        "Name",
                        [
                            "pending",
                            "running",
                            "shutting-down",
                            "terminated",
                            "stopping",
                            "stopped",
                        ],
                    ),
                ],
            ),
            Str("StateTransitionReason"),
            Str("SubnetId"),
            Str("VpcId"),
            Choice(
                "Architecture",
                [
                    "i386",
                    "x86_64",
                    "arm64",
                ],
            ),
            List(
                "BlockDeviceMappings",
                [
                    Str("DeviceName"),
                    Dict(
                        "Ebs",
                        [
                            Timestamp("AttachTime"),
                            BoolChoice("DeleteOnTermination"),
                            Choice(
                                "Status",
                                [
                                    "attaching",
                                    "attached",
                                    "detaching",
                                    "detached",
                                ],
                            ),
                            Str("VolumeId"),
                        ],
                    ),
                ],
            ),
            Str("ClientToken"),
            BoolChoice("EbsOptimized"),
            BoolChoice("EnaSupport"),
            Choice(
                "Hypervisor",
                [
                    "ovm",
                    "xen",
                ],
            ),
            Dict(
                "IamInstanceProfile",
                [
                    Str("Arn"),
                    Str("Id"),
                ],
            ),
            Choice(
                "InstanceLifecycle",
                [
                    "spot",
                    "scheduled",
                ],
            ),
            List(
                "ElasticGpuAssociations",
                [
                    Str("ElasticGpuId"),
                    Str("ElasticGpuAssociationId"),
                    Str("ElasticGpuAssociationState"),
                    Str("ElasticGpuAssociationTime"),
                ],
            ),
            List(
                "ElasticInferenceAcceleratorAssociations",
                [
                    Str("ElasticInferenceAcceleratorArn"),
                    Str("ElasticInferenceAcceleratorAssociationId"),
                    Str("ElasticInferenceAcceleratorAssociationState"),
                    Timestamp("ElasticInferenceAcceleratorAssociationTime"),
                ],
            ),
            List(
                "NetworkInterfaces",
                [
                    Dict(
                        "Association",
                        [
                            Str("IpOwnerId"),
                            Str("PublicDnsName"),
                            Str("PublicIp"),
                        ],
                    ),
                    Dict(
                        "Attachment",
                        [
                            Timestamp("AttachTime"),
                            Str("AttachmentId"),
                            BoolChoice("DeleteOnTermination"),
                            Int("DeviceIndex"),
                            Choice(
                                "Status",
                                [
                                    "attaching",
                                    "attached",
                                    "detaching",
                                    "detached",
                                ],
                            ),
                        ],
                    ),
                    Str("Description"),
                    List(
                        "Groups",
                        [
                            Str("GroupName"),
                            Str("GroupId"),
                        ],
                    ),
                    List(
                        "Ipv6Addresses",
                        [
                            Str("Ipv6Address"),
                        ],
                    ),
                    Str("MacAddress"),
                    Str("NetworkInterfaceId"),
                    Str("OwnerId"),
                    Str("PrivateDnsName"),
                    Str("PrivateIpAddress"),
                    List(
                        "PrivateIpAddresses",
                        [
                            Dict(
                                "Association",
                                [
                                    Str("IpOwnerId"),
                                    Str("PublicDnsName"),
                                    Str("PublicIp"),
                                ],
                            ),
                            BoolChoice("Primary"),
                            Str("PrivateDnsName"),
                            Str("PrivateIpAddress"),
                        ],
                    ),
                    BoolChoice("SourceDestCheck"),
                    Choice(
                        "Status",
                        [
                            "available",
                            "associated",
                            "attaching",
                            "in-use",
                            "detaching",
                        ],
                    ),
                    Str("SubnetId"),
                    Str("VpcId"),
                ],
            ),
            Str("RootDeviceName"),
            Choice(
                "RootDeviceType",
                [
                    "ebs",
                    "instance-store",
                ],
            ),
            List(
                "SecurityGroups",
                [
                    Str("GroupName"),
                    Str("GroupId"),
                ],
            ),
            BoolChoice("SourceDestCheck"),
            Str("SpotInstanceRequestId"),
            Str("SriovNetSupport"),
            Dict(
                "StateReason",
                [
                    Str("Code"),
                    Str("Message"),
                ],
            ),
            List(
                "Tags",
                [
                    Str("Key"),
                    Str("Value"),
                ],
            ),
            Choice(
                "VirtualizationType",
                [
                    "hvm",
                    "paravirtual",
                ],
            ),
            Dict(
                "CpuOptions",
                [
                    Int("CoreCount"),
                    Int("ThreadsPerCore"),
                ],
            ),
            Str("CapacityReservationId"),
            Dict(
                "CapacityReservationSpecification",
                [
                    Choice(
                        "CapacityReservationPreference",
                        [
                            "open",
                            "none",
                        ],
                    ),
                    Dict(
                        "CapacityReservationTarget",
                        [
                            Str("CapacityReservationId"),
                        ],
                    ),
                ],
            ),
            Dict(
                "HibernationOptions",
                [
                    BoolChoice("Configured"),
                ],
            ),
            List(
                "Licenses",
                [
                    Str("LicenseConfigurationArn"),
                ],
            ),
        ]


class EC2DescribeVolumesIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            List(
                "Attachments",
                [
                    Timestamp("AttachTime"),
                    Str("Device"),
                    Str("InstanceId"),
                    Choice(
                        "State",
                        [
                            "attaching",
                            "attached",
                            "detaching",
                            "detached",
                            "busy",
                        ],
                    ),
                    Str("VolumeId"),
                    BoolChoice("DeleteOnTermination"),
                ],
            ),
            Str("AvailabilityZone"),
            Timestamp("CreateTime"),
            BoolChoice("Encrypted"),
            Str("KmsKeyId"),
            Int("Size"),
            Str("SnapshotId"),
            Choice(
                "State",
                [
                    "creating",
                    "available",
                    "in-use",
                    "deleting",
                    "deleted",
                    "error",
                ],
            ),
            Str("VolumeId"),
            Int("Iops"),
            List(
                "Tags",
                [
                    Str("Key"),
                    Str("Value"),
                ],
            ),
            Choice(
                "VolumeType",
                [
                    "standard",
                    "io1",
                    "gp2",
                    "sc1",
                    "st1",
                ],
            ),
        ]


class EC2DescribeSnapshotsIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            Str("DataEncryptionKeyId"),
            Str("Description"),
            BoolChoice("Encrypted"),
            Str("KmsKeyId"),
            Str("OwnerId"),
            Str("Progress"),
            Str("SnapshotId"),
            Timestamp("StartTime"),
            Choice(
                "State",
                [
                    "pending",
                    "completed",
                    "error",
                ],
            ),
            Str("StateMessage"),
            Str("VolumeId"),
            Int("VolumeSize"),
            Str("OwnerAlias"),
            List(
                "Tags",
                [
                    Str("Key"),
                    Str("Value"),
                ],
            ),
        ]


class EC2DescribeVolumeStatusIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            List(
                "Actions",
                [
                    Str("Code"),
                    Str("Description"),
                    Str("EventId"),
                    Str("EventType"),
                ],
            ),
            Str("AvailabilityZone"),
            List(
                "Events",
                [
                    Str("Description"),
                    Str("EventId"),
                    Str("EventType"),
                    Timestamp("NotAfter"),
                    Timestamp("NotBefore"),
                ],
            ),
            Str("VolumeId"),
            Dict(
                "VolumeStatus",
                [
                    List(
                        "Details",
                        [
                            Choice(
                                "Name",
                                [
                                    "io-enabled",
                                    "io-performance",
                                ],
                            ),
                            Str("Status"),
                        ],
                    ),
                    Choice(
                        "Status",
                        [
                            "ok",
                            "impaired",
                            "insufficient-data",
                        ],
                    ),
                ],
            ),
        ]


class EC2DescribeTagsIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            Str("Key"),
            Str("ResourceId"),
            Choice(
                "ResourceType",
                [
                    "client-vpn-endpoint",
                    "customer-gateway",
                    "dedicated-host",
                    "dhcp-options",
                    "elastic-ip",
                    "fleet",
                    "fpga-image",
                    "host-reservation",
                    "image",
                    "instance",
                    "internet-gateway",
                    "launch-template",
                    "natgateway",
                    "network-acl",
                    "network-interface",
                    "reserved-instances",
                    "route-table",
                    "security-group",
                    "snapshot",
                    "spot-instances-request",
                    "subnet",
                    "transit-gateway",
                    "transit-gateway-attachment",
                    "transit-gateway-route-table",
                    "volume",
                    "vpc",
                    "vpc-peering-connection",
                    "vpn-connection",
                    "vpn-gateway",
                ],
            ),
            Str("Value"),
        ]


# .
#   .--DynamoDB-------------------------------------------------------------


class DynamoDBDescribeLimitsIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            Int("AccountMaxReadCapacityUnits"),
            Int("AccountMaxWriteCapacityUnits"),
            Int("TableMaxReadCapacityUnits"),
            Int("TableMaxWriteCapacityUnits"),
        ]


class DynamoDBDescribeTableIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            List(
                "AttributeDefinitions",
                [Str("AttributeName"), Choice("AttributeType", ["S", "N", "B"])],
            ),
            Str("TableName"),
            List("KeySchema", [Str("AttributeName"), Choice("KeyType", ["HASH", "RANGE"])]),
            Choice(
                "TableStatus",
                [
                    "CREATING",
                    "UPDATING",
                    "DELETING",
                    "ACTIVE",
                    "INACCESSIBLE_ENCRYPTION_CREDENTIALS",
                    "ARCHIVING",
                    "ARCHIVED",
                ],
            ),
            Timestamp("CreationDateTime"),
            Dict(
                "ProvisionedThroughput",
                [
                    Timestamp("LastIncreaseDateTime"),
                    Timestamp("LastDecreaseDateTime"),
                    Int("NumberOfDecreasesToday"),
                    # to also obtain on-demand tables with 0 provisioned throughput
                    Choice("ReadCapacityUnits", [0, 100]),
                    Choice("WriteCapacityUnits", [0, 100]),
                ],
            ),
            Int("TableSizeBytes"),
            Int("ItemCount"),
            Str("TableArn"),
            Str("TableId"),
            Dict(
                "BillingModeSummary",
                [
                    Choice("BillingMode", ["PROVISIONED", "PAY_PER_REQUEST"]),
                    Timestamp("LastUpdateToPayPerRequestDateTime"),
                ],
            ),
            List(
                "LocalSecondaryIndexes",
                [
                    Str("IndexName"),
                    List(
                        "KeySchema",
                        [
                            Str("AttributeName"),
                            Choice("KeyType", ["HASH", "RANGE"]),
                        ],
                    ),
                    Dict(
                        "Projection",
                        [
                            Choice("ProjectionType", ["ALL", "KEYS_ONLY", "INCLUDE"]),
                            Enum("NonKeyAttributes"),
                        ],
                    ),
                    Int("IndexSizeBytes"),
                    Int("ItemCount"),
                    Str("IndexArn"),
                ],
            ),
            List(
                "GlobalSecondaryIndexes",
                [
                    Str("IndexName"),
                    List(
                        "KeySchema",
                        [
                            Str("AttributeName"),
                            Choice("KeyType", ["HASH", "RANGE"]),
                        ],
                    ),
                    Dict(
                        "Projection",
                        [
                            Choice("ProjectionType", ["ALL", "KEYS_ONLY", "INCLUDE"]),
                            Enum("NonKeyAttributes"),
                        ],
                    ),
                    Choice("IndexStatus", ["CREATING", "UPDATING", "DELETING", "ACTIVE"]),
                    BoolChoice("Backfilling"),
                    Dict(
                        "ProvisionedThroughput",
                        [
                            Timestamp("LastIncreaseDateTime"),
                            Timestamp("LastDecreaseDateTime"),
                            Int("NumberOfDecreasesToday"),
                            Int("ReadCapacityUnits"),
                            Int("WriteCapacityUnits"),
                        ],
                    ),
                    Int("IndexSizeBytes"),
                    Int("ItemCount"),
                    Str("IndexArn"),
                ],
            ),
            Dict(
                "StreamSpecification",
                [
                    BoolChoice("StreamEnabled"),
                    Choice(
                        "StreamViewType",
                        ["NEW_IMAGE", "OLD_IMAGE", "NEW_AND_OLD_IMAGES", "KEYS_ONLY"],
                    ),
                ],
            ),
            Str("LatestStreamLabel"),
            Str("LatestStreamArn"),
            Str("GlobalTableVersion"),
            List(
                "Replicas",
                [
                    Str("RegionName"),
                    Choice(
                        "ReplicaStatus",
                        ["CREATING", "CREATION_FAILED", "UPDATING", "DELETING", "ACTIVE"],
                    ),
                    Str("ReplicaStatusDescription"),
                    Str("ReplicaStatusPercentProgress"),
                    Str("KMSMasterKeyId"),
                    Dict("ProvisionedThroughputOverride", [Int("ReadCapacityUnits")]),
                    List(
                        "GlobalSecondaryIndexes",
                        [
                            Str("IndexName"),
                            Dict("ProvisionedThroughputOverride", [Int("ReadCapacityUnits")]),
                        ],
                    ),
                ],
            ),
            Dict(
                "RestoreSummary",
                [
                    Str("SourceBackupArn"),
                    Str("SourceTableArn"),
                    Timestamp("RestoreDateTime"),
                    BoolChoice("RestoreInProgress"),
                ],
            ),
            Dict(
                "SSEDescription",
                [
                    Choice("Status", ["ENABLING", "ENABLED", "DISABLING", "DISABLED", "UPDATING"]),
                    Choice("SSEType", ["AES256", "KMS"]),
                    Str("KMSMasterKeyArn"),
                    Timestamp("InaccessibleEncryptionDateTime"),
                ],
            ),
            Dict(
                "ArchivalSummary",
                [
                    Timestamp("ArchivalDateTime"),
                    Str("ArchivalReason"),
                    Str("ArchivalBackupArn"),
                ],
            ),
        ]


class DynamoDBListTagsOfResourceIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            Str("Key"),
            Str("Value"),
        ]


# .
#   .--WAFV2----------------------------------------------------------------


class WAFV2ListOperationIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [Str("Name"), Str("Id"), Str("Description"), Str("LockToken"), Str("ARN")]


class WAFV2GetWebACLIB(InstanceBuilder):
    def _field_to_match(self):
        return Dict(
            "FieldToMatch",
            [
                Dict("SingleHeader", [Str("Name")]),
                Dict("SingleQueryArgument", [Str("Name")]),
                Dict("AllQueryArguments", []),
                Dict("UriPath", []),
                Dict("QueryString", []),
                Dict("Body", []),
                Dict("Method", []),
            ],
        )

    def _text_transformations(self):
        return List(
            "TextTransformations",
            [
                Int("Priority"),
                Choice(
                    "Type",
                    [
                        "NONE",
                        "COMPRESS_WHITE_SPACE",
                        "HTML_ENTITY_DECODE",
                        "LOWERCASE",
                        "CMD_LINE",
                        "URL_DECODE",
                    ],
                ),
            ],
        )

    def _visibility_config(self):
        return Dict(
            "VisibilityConfig",
            [
                BoolChoice("SampledRequestsEnabled"),
                BoolChoice("CloudWatchMetricsEnabled"),
                Str("MetricName"),
            ],
        )

    def _process_firewall_manager_rule_groups(self, key):
        return List(
            key,
            [
                Str("Name"),
                Int("Priority"),
                Dict(
                    "FirewallManagerStatement",
                    [
                        Dict(
                            "ManagedRuleGroupStatement",
                            [Str("VendorName"), Str("Name"), List("ExcludedRules", [Str("Name")])],
                        ),
                        Dict(
                            "RuleGroupReferenceStatement",
                            [Str("Name"), List("ExcludedRules", [Str("Name")])],
                        ),
                    ],
                ),
                Dict("OverrideAction", [Dict("Count", []), Dict("None", [])]),
                self._visibility_config(),
            ],
        )

    def _fill_instance(self) -> Iterable[Entity]:
        return [
            Str("Name"),
            Str("Id"),
            Str("ARN"),
            Dict("DefaultAction", [Dict("Block", []), Dict("Allow", [])]),
            Str("Description"),
            List(
                "Rules",
                [
                    Str("Name"),
                    Int("Priority"),
                    Dict(
                        "Statement",
                        [
                            Dict(
                                "ByteMatchStatement",
                                [
                                    Bytes("SearchString"),
                                    self._field_to_match(),
                                    self._text_transformations(),
                                    Choice(
                                        "PositionalConstraint",
                                        [
                                            "EXACTLY",
                                            "STARTS_WITH",
                                            "ENDS_WITH",
                                            "CONTAINS",
                                            "CONTAINS_WORD",
                                        ],
                                    ),
                                ],
                            ),
                            Dict(
                                "SqliMatchStatement",
                                [self._field_to_match(), self._text_transformations()],
                            ),
                            Dict(
                                "XssMatchStatement",
                                [self._field_to_match(), self._text_transformations()],
                            ),
                            Dict(
                                "SizeConstraintStatement",
                                [
                                    self._field_to_match(),
                                    Choice(
                                        "ComparisonOperator", ["EQ", "NE", "LE", "LT", "GE", "GT"]
                                    ),
                                    Int("Size"),
                                    self._text_transformations(),
                                ],
                            ),
                            Dict("GeoMatchStatement", [Enum("CountryCodes")]),
                            Dict(
                                "RuleGroupReferenceStatement",
                                [Str("ARN"), List("ExcludedRules", [Str("Name")])],
                            ),
                            Dict("IPSetReferenceStatement", [Str("ARN")]),
                            Dict(
                                "RegexPatternSetReferenceStatement",
                                [Str("ARN"), self._field_to_match(), self._text_transformations()],
                            ),
                            Dict(
                                "RateBasedStatement",
                                [
                                    Int("Limit"),
                                    Str("AggregateKeyType"),
                                    Dict("ScopeDownStatement", []),
                                ],
                            ),
                            Dict("AndStatement", [List("Statements", [])]),
                            Dict("OrStatement", [List("Statements", [])]),
                            Dict("NotStatement", [Dict("ScopeDownStatement", [])]),
                            Dict(
                                "Statement",
                                [
                                    Dict(
                                        "ManagedRuleGroupStatement",
                                        [
                                            Str("VendorName"),
                                            Str("Name"),
                                            List("ExcludedRules", [Str("Name")]),
                                        ],
                                    )
                                ],
                            ),
                            Dict(
                                "Action", [Dict("Block", []), Dict("Allow", []), Dict("Count", [])]
                            ),
                            Dict("OverrideAction", [Dict("Count", []), Dict("None", [])]),
                            self._visibility_config(),
                        ],
                    ),
                ],
            ),
            self._visibility_config(),
            Int("Capacity"),
            self._process_firewall_manager_rule_groups("PreProcessFirewallManagerRuleGroups"),
            self._process_firewall_manager_rule_groups("PostProcessFirewallManagerRuleGroups"),
            BoolChoice("ManagedByFirewallManager"),
        ]


class WAFV2ListTagsForResourceIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [Str("ResourceARN"), List("TagList", [Str("Key"), Str("Value")])]


# .
#   .--fake clients--------------------------------------------------------.
#   |           __       _               _ _            _                  |
#   |          / _| __ _| | _____    ___| (_) ___ _ __ | |_ ___            |
#   |         | |_ / _` | |/ / _ \  / __| | |/ _ \ '_ \| __/ __|           |
#   |         |  _| (_| |   <  __/ | (__| | |  __/ | | | |_\__ \           |
#   |         |_|  \__,_|_|\_\___|  \___|_|_|\___|_| |_|\__|___/           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class FakeCloudwatchClient:
    def describe_alarms(self, AlarmNames=None):
        alarms = CloudwatchDescribeAlarmsIB.create_instances(amount=2)
        if AlarmNames:
            alarms = [alarm for alarm in alarms if alarm["AlarmName"] in AlarmNames]
        return {"MetricAlarms": alarms, "NextToken": "string"}

    def get_metric_data(self, MetricDataQueries, StartTime="START", EndTime="END"):
        results = []
        for query in MetricDataQueries:
            results.append(
                {
                    "Id": query["Id"],
                    "Label": query["Label"],
                    "Timestamps": [
                        "1970-01-01",
                    ],
                    "Values": [
                        123.0,
                    ],
                    "StatusCode": "'Complete' | 'InternalError' | 'PartialData'",
                    "Messages": [
                        {"Code": "string1", "Value": "string1"},
                    ],
                }
            )
        return {
            "MetricDataResults": results,
            "NextToken": "string",
            "Messages": [
                {"Code": "string", "Value": "string"},
            ],
        }


class QueryResults(TypedDict):
    status: str
    results: Mapping[str, Sequence[Mapping[str, str]]]


FAKE_CLOUDWATCH_CLIENT_LOGS_CLIENT_DEFAULT_RESPONSE: QueryResults = {
    "status": "Complete",
    "results": {
        "arn:aws:lambda:eu-central-1:710145618630:function:my_python_test_function": [
            {"field": "max_memory_used_bytes", "value": "52000000"},
            {"field": "max_init_duration_ms", "value": "1702.11"},
            {"field": "count_cold_starts", "value": "2"},
            {"field": "count_invocations", "value": "4"},
        ]
    },
}


class QueryId(TypedDict):
    queryId: str


class FakeCloudwatchClientLogsClient:
    def start_query(
        self, logGroupName: str, startTime: int, endTime: int, queryString: str
    ) -> QueryId:
        return {"queryId": "MY_QUERY_ID"}

    def get_query_results(self, queryId: str) -> QueryResults:
        return FAKE_CLOUDWATCH_CLIENT_LOGS_CLIENT_DEFAULT_RESPONSE

    def stop_query(self, queryId: str):
        pass


class FakeServiceQuotasClient:
    def list_service_quotas(self, ServiceCode):
        q_val = Float("Value")
        return {
            "Quotas": [
                {"QuotaName": name, "Value": q_val.create(None, None)}
                for name in [
                    "Running On-Demand F instances",
                    "Running On-Demand G instances",
                    "Running On-Demand P instances",
                    "Running On-Demand Standard (A, C, D, H, I, M, R, T, Z) instances",
                    "Running On-Demand X instances",
                ]
            ]
        }


#   .--Lambda----------------------------------


class LambdaListFunctionsIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return {
            Str("FunctionName"),
            Str("FunctionArn", value="arn:aws:lambda:eu-central-1:123456789:function:FunctionName"),
            Choice("Runtime", ["nodejs", "python2.7", "dotnetcore3.1"]),
            Str("Role"),
            Str("Handler"),
            Int("CodeSize"),
            Str("Description"),
            Int("Timeout"),
            Int("MemorySize"),
            Str("LastModified"),
            Str("CodeSha256"),
            Str("Version"),
            Dict(
                "VpcConfig",
                [
                    List("SubnetIds", []),
                    List("SecurityGroupIds", []),
                    List("DeadLetterConfig", []),
                    List("DeadLetterConfig", []),
                    Dict(
                        "Environment",
                        [
                            Dict("Variables", []),
                            Dict(
                                "Error",
                                [
                                    Str("ErrorCode"),
                                    Str("Message"),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            Str("KMSKeyArn"),
            Dict(
                "TracingConfig",
                [
                    Choice("Mode", ["Active", "PassThrough"]),
                ],
            ),
            Str("MasterArn"),
            Str("RevisionId"),
            List("Layers", []),
            Choice("State", ["Pending", "Active", "Inactive", "Failed"]),
            Str("StateReason"),
            Choice("StateReasonCode", ["Idle", "Creating", "Restoring"]),
            Str("LastUpdateStatus"),
            Str("LastUpdateStatusReason"),
            Choice(
                "LastUpdateStatusReasonCode", ["EniLimitExceeded", "InsufficientRolePermissions"]
            ),
            Dict(
                "FileSystemConfigs",
                [
                    Str("Arn"),
                    Str("LocalMountPath"),
                ],
            ),
            Choice("PackageType", ["Zip", "Image"]),
            Dict(
                "ImageConfigResponse",
                [
                    Dict(
                        "ImageConfig",
                        [
                            Str("EntryPoint"),
                            Str("Command"),
                            Str("WorkingDirectory"),
                        ],
                    ),
                    Dict(
                        "Error",
                        [
                            Str("ErrorCode"),
                            Str("Message"),
                        ],
                    ),
                ],
            ),
            Str("SigningProfileVersionArn"),
            Str("SigningJobArn"),
        }


class LambdaListTagsInstancesIB(DictInstanceBuilder):
    def _key(self):
        return Str("Tag")

    def _value(self):
        return Str("Value")


class LambdaListProvisionedConcurrencyConfigsIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return {
            Str(
                "FunctionArn",
                value="arn:aws:lambda:eu-central-1:123456789:function:FunctionName:Alias",
            ),
            Int("RequestedProvisionedConcurrentExecutions"),
            Int("AvailableProvisionedConcurrentExecutions"),
            Int("AllocatedProvisionedConcurrentExecutions"),
            Choice("Status", ["IN_PROGRESS", "READY", "FAILED"]),
            Str("StatusReason"),
            Str("LastModified"),
        }


class SNSListSubscriptionsIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [
            Str("SubscriptionArn"),
            Str("Owner"),
            Str("Protocol"),
            Str("Endpoint"),
            Str("TopicArn"),
        ]


class SNSListTopicsIB(InstanceBuilder):
    def _fill_instance(self) -> Iterable[Entity]:
        return [Str("TopicArn")]
