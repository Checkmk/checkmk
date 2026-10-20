#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The one place that decides which host the data of an AWS resource goes to.

Every section asks target_host for the host of its results, or ec2_instance_hosts for
the hosts of EC2 instances. Data about the AWS account or a region as a whole goes to the
source host, the host that runs the special agent, or to the piggyback host of the
account when the agent monitors a list of accounts.
Some resources get a piggyback host of their own. Each resource type has its own host
name function below.
"""

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from typing import assert_never, Final, NewType, overload, Self

from pydantic import BaseModel, Field

from .config import CloudFrontHostAssignment, HostNaming, NamingConvention

TargetHost = NewType("TargetHost", str)
"""The name of a piggyback host."""

SOURCE_HOST: Final = None
"""The host that runs the special agent. The agent writes no piggyback header for it.

target_host returns it only when the account has no piggyback host of its own.
"""


@dataclass(frozen=True)
class AccountScope:
    """Data about the AWS account or one of its regions as a whole."""


class _Instance(BaseModel):
    private_ip_address: str | None = Field(None, alias="PrivateIpAddress")
    private_dns_name: str | None = Field(None, alias="PrivateDnsName")
    instance_id: str = Field(..., alias="InstanceId")


@dataclass(frozen=True)
class EC2Instance:
    instance_id: str
    private_ip_address: str | None
    private_dns_name: str | None
    region: str

    @classmethod
    def from_api(cls, instance: Mapping[str, object], region: str) -> Self:
        parsed = _Instance.model_validate(instance)
        return cls(
            instance_id=parsed.instance_id,
            private_ip_address=parsed.private_ip_address,
            private_dns_name=parsed.private_dns_name,
            region=region,
        )


@dataclass(frozen=True)
class EBSAttachment:
    """An EBS volume attached to an EC2 instance.

    instance_host is the host of that instance, or None if the agent does not monitor
    the instance.
    """

    instance_host: TargetHost | None


@dataclass(frozen=True)
class ClassicLoadBalancer:
    dns_name: str


@dataclass(frozen=True)
class LoadBalancerV2:
    dns_name: str


@dataclass(frozen=True)
class DynamoDBTable:
    name: str
    region: str


@dataclass(frozen=True)
class WAFV2WebACL:
    name: str
    region: str
    """The region of a regional web ACL, or "CloudFront" for a global one."""


@dataclass(frozen=True)
class CloudFrontDistribution:
    origin_domain: str | None
    """The domain name of the first origin, if the distribution has one."""


@dataclass(frozen=True)
class GlacierVault:
    name: str


@dataclass(frozen=True)
class S3Bucket:
    name: str


@dataclass(frozen=True)
class ElastiCacheNode:
    """An ElastiCache node, a cache cluster in the AWS API."""

    node_id: str


@dataclass(frozen=True)
class RDSInstance:
    instance_id: str


@dataclass(frozen=True)
class SNSTopic:
    name: str


# Each of these resources always goes to a piggyback host of its own.
PiggybackResource = (
    ClassicLoadBalancer
    | LoadBalancerV2
    | DynamoDBTable
    | WAFV2WebACL
    | GlacierVault
    | S3Bucket
    | ElastiCacheNode
    | RDSInstance
    | SNSTopic
)

HostedResource = AccountScope | EBSAttachment | CloudFrontDistribution | PiggybackResource


@overload
def target_host(resource: PiggybackResource, naming: HostNaming) -> TargetHost: ...


@overload
def target_host(resource: HostedResource, naming: HostNaming) -> TargetHost | None: ...


def target_host(resource: HostedResource, naming: HostNaming) -> TargetHost | None:
    """Decide the host that the data of an AWS resource goes to.

    None is SOURCE_HOST.
    """
    match resource:
        case AccountScope():
            return _account_scope_host(naming.account)
        case EBSAttachment():
            return _ebs_attachment_host(resource, naming.account)
        case ClassicLoadBalancer():
            return _classic_load_balancer_host(resource)
        case LoadBalancerV2():
            return _load_balancer_v2_host(resource)
        case DynamoDBTable():
            return _dynamodb_table_host(resource)
        case WAFV2WebACL():
            return _wafv2_web_acl_host(resource)
        case CloudFrontDistribution():
            return _cloudfront_distribution_host(resource, naming)
        case GlacierVault():
            return _glacier_vault_host(resource)
        case S3Bucket():
            return _s3_bucket_host(resource)
        case ElastiCacheNode():
            return _elasticache_node_host(resource)
        case RDSInstance():
            return _rds_instance_host(resource)
        case SNSTopic():
            return _sns_topic_host(resource)
        case _:
            assert_never(resource)


def ec2_instance_hosts[T: Mapping[str, object]](
    instances: Iterable[T], region: str, naming: HostNaming
) -> Iterator[tuple[TargetHost, T]]:
    """Pair the EC2 instances of the API with their hosts.

    The agent does not monitor an instance without a host name, so it is left out.
    """
    for instance in instances:
        host = _ec2_instance_host(EC2Instance.from_api(instance, region), naming.ec2)
        if host is not None:
            yield host, instance


def _account_scope_host(account_host: str | None) -> TargetHost | None:
    return SOURCE_HOST if account_host is None else TargetHost(account_host)


def _ec2_instance_host(instance: EC2Instance, convention: NamingConvention) -> TargetHost | None:
    # PrivateIpAddress and InstanceId is available although the instance is stopped
    # When we terminate an instance, the instance gets the state "terminated":
    # https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-lifecycle.html
    # The instance remains in this state about 60 minutes, after 60 minutes the
    # instance is no longer visible in the console.
    # In this case we do not deliever any data for this piggybacked host such that
    # the services go stable and Check_MK service reports "CRIT - Got not information".
    match convention:
        case NamingConvention.private_dns_name:
            return TargetHost(instance.private_dns_name) if instance.private_dns_name else None
        case NamingConvention.ip_region_instance:
            if instance.private_ip_address and instance.instance_id:
                return TargetHost(
                    f"{instance.private_ip_address}-{instance.region}-{instance.instance_id}"
                )
            return None
        case _:
            assert_never(convention)


def _ebs_attachment_host(attachment: EBSAttachment, account_host: str | None) -> TargetHost | None:
    if attachment.instance_host is None:
        return _account_scope_host(account_host)
    return attachment.instance_host


def _classic_load_balancer_host(load_balancer: ClassicLoadBalancer) -> TargetHost:
    return TargetHost(load_balancer.dns_name)


def _load_balancer_v2_host(load_balancer: LoadBalancerV2) -> TargetHost:
    return TargetHost(load_balancer.dns_name)


def _dynamodb_table_host(table: DynamoDBTable) -> TargetHost:
    return _hostname_from_name_and_region(table.name, table.region)


def _wafv2_web_acl_host(web_acl: WAFV2WebACL) -> TargetHost:
    return _hostname_from_name_and_region(web_acl.name, web_acl.region)


def _cloudfront_distribution_host(
    distribution: CloudFrontDistribution, naming: HostNaming
) -> TargetHost | None:
    if naming.cloudfront is CloudFrontHostAssignment.origin_domain and distribution.origin_domain:
        return TargetHost(distribution.origin_domain)
    return _account_scope_host(naming.account)


def _glacier_vault_host(vault: GlacierVault) -> TargetHost:
    return TargetHost(vault.name)


def _s3_bucket_host(bucket: S3Bucket) -> TargetHost:
    return TargetHost(bucket.name)


def _elasticache_node_host(node: ElastiCacheNode) -> TargetHost:
    return TargetHost(node.node_id)


def _rds_instance_host(instance: RDSInstance) -> TargetHost:
    return TargetHost(instance.instance_id)


def _sns_topic_host(topic: SNSTopic) -> TargetHost:
    return TargetHost(topic.name)


def _hostname_from_name_and_region(name: str, region: str) -> TargetHost:
    """
    We add the region to the the hostname because resources in different regions might have the
    same names (for example replicated DynamoDB tables).
    """
    return TargetHost(f"{name}_{region}")
