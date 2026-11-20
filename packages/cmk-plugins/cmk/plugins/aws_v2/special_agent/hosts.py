#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The one place that decides which host the data of an AWS resource goes to.

Every section asks target_host for the host of its results, or ec2_instance_hosts for
the hosts of EC2 instances. Data about the AWS account or a region as a whole goes to the
piggyback host of the account, named aws_account_ followed by the account ID.
Some resources get a piggyback host of their own. Each resource type has its own host
name function below.
"""

import hashlib
import re
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from typing import assert_never, NewType, Self

from pydantic import BaseModel, Field

from .config import (
    CloudFrontHostAssignment,
    HostNaming,
    NamingConvention,
    NonEC2PiggybackTemplate,
    TagNaming,
)

TargetHost = NewType("TargetHost", str)
"""The name of a piggyback host."""


INVALID_HOST_NAME_CHAR = re.compile(r"[^-0-9a-zA-Z_.]")
PIGGYBACK_HASH_LENGTH = 8
_MAX_HOST_NAME_LENGTH = 240


@dataclass(frozen=True)
class AccountScope:
    """Data about the AWS account or one of its regions as a whole."""


class _Tag(BaseModel):
    key: str = Field(..., alias="Key")
    value: str = Field(..., alias="Value")


class _Instance(BaseModel):
    private_ip_address: str | None = Field(None, alias="PrivateIpAddress")
    private_dns_name: str | None = Field(None, alias="PrivateDnsName")
    instance_id: str = Field(..., alias="InstanceId")
    tags: list[_Tag] = Field(default_factory=list, alias="Tags")


@dataclass(frozen=True)
class EC2Instance:
    instance_id: str
    private_ip_address: str | None
    private_dns_name: str | None
    region: str
    tags: Mapping[str, str]

    @classmethod
    def from_api(cls, instance: Mapping[str, object], region: str) -> Self:
        parsed = _Instance.model_validate(instance)
        return cls(
            instance_id=parsed.instance_id,
            private_ip_address=parsed.private_ip_address,
            private_dns_name=parsed.private_dns_name,
            region=region,
            tags={tag.key: tag.value for tag in parsed.tags},
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
    name: str
    arn: str  # Constructed from the name by us, the API doesn't include it.


@dataclass(frozen=True)
class LoadBalancerV2:
    name: str
    arn: str


@dataclass(frozen=True)
class DynamoDBTable:
    name: str
    arn: str


@dataclass(frozen=True)
class WAFV2WebACL:
    name: str
    arn: str


@dataclass(frozen=True)
class CloudFrontDistribution:
    distribution_id: str
    origin_domain: str | None
    """The domain name of the first origin, if the distribution has one."""
    arn: str


@dataclass(frozen=True)
class GlacierVault:
    name: str
    arn: str


@dataclass(frozen=True)
class S3Bucket:
    name: str
    arn: str


@dataclass(frozen=True)
class ElastiCacheNode:
    """An ElastiCache node, a cache cluster in the AWS API."""

    node_id: str
    arn: str


@dataclass(frozen=True)
class RDSInstance:
    instance_id: str
    arn: str


@dataclass(frozen=True)
class SNSTopic:
    name: str
    arn: str


@dataclass(frozen=True)
class LambdaFunction:
    name: str
    arn: str


@dataclass(frozen=True)
class ECSCluster:
    name: str
    arn: str


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
    | LambdaFunction
    | ECSCluster
)

HostedResource = AccountScope | EBSAttachment | CloudFrontDistribution | PiggybackResource


def target_host(resource: HostedResource, naming: HostNaming) -> TargetHost:
    """Decide the host that the data of an AWS resource goes to."""
    match resource:
        case AccountScope():
            return account_host(naming.account_id)
        case EBSAttachment():
            return _ebs_attachment_host(resource, naming.account_id)
        case ClassicLoadBalancer():
            return _classic_load_balancer_host(resource, naming.non_ec2)
        case LoadBalancerV2():
            return _load_balancer_v2_host(resource, naming.non_ec2)
        case DynamoDBTable():
            return _dynamodb_table_host(resource, naming.non_ec2)
        case WAFV2WebACL():
            return _wafv2_web_acl_host(resource, naming.non_ec2)
        case CloudFrontDistribution():
            return _cloudfront_distribution_host(resource, naming)
        case GlacierVault():
            return _glacier_vault_host(resource, naming.non_ec2)
        case S3Bucket():
            return _s3_bucket_host(resource, naming.non_ec2)
        case ElastiCacheNode():
            return _elasticache_node_host(resource, naming.non_ec2)
        case RDSInstance():
            return _rds_instance_host(resource, naming.non_ec2)
        case SNSTopic():
            return _sns_topic_host(resource, naming.non_ec2)
        case LambdaFunction():
            return _lambda_function_host(resource, naming.non_ec2)
        case ECSCluster():
            return _ecs_cluster_host(resource, naming.non_ec2)
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


def account_host(account_id: str | None) -> TargetHost:
    if account_id is None:
        raise ValueError("The host of account data needs a config scoped to an account")
    return TargetHost(f"aws_account_{account_id}")


def _ec2_instance_host(
    instance: EC2Instance, convention: NamingConvention | TagNaming
) -> TargetHost | None:
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
        case TagNaming(key=key):
            value = instance.tags.get(key)
            return None if value is None else _host_name_from_tag_value(value)
        case _:
            assert_never(convention)


def _host_name_from_tag_value(value: str) -> TargetHost | None:
    """Replace each character that a host name cannot contain with "_".

    A value that gives no valid host name returns None: an empty value, a too long value,
    or a value that starts with "-" or ".".
    """
    if len(value) > _MAX_HOST_NAME_LENGTH:
        return None
    host_name = _sanitize_name(value)
    if not host_name or host_name[0] in "-.":
        return None
    return TargetHost(host_name)


def _ebs_attachment_host(attachment: EBSAttachment, account_id: str | None) -> TargetHost:
    if attachment.instance_host is None:
        return account_host(account_id)
    return attachment.instance_host


def _classic_load_balancer_host(
    load_balancer: ClassicLoadBalancer, template: NonEC2PiggybackTemplate
) -> TargetHost:
    return _hostname_with_hashed_arn(
        "elasticloadbalancing_loadbalancer", load_balancer.name, load_balancer.arn, template
    )


def _load_balancer_v2_host(
    load_balancer: LoadBalancerV2, template: NonEC2PiggybackTemplate
) -> TargetHost:
    return _hostname_with_hashed_arn(
        "elasticloadbalancing_loadbalancer", load_balancer.name, load_balancer.arn, template
    )


def _dynamodb_table_host(table: DynamoDBTable, template: NonEC2PiggybackTemplate) -> TargetHost:
    return _hostname_with_hashed_arn("dynamodb_table", table.name, table.arn, template)


def _wafv2_web_acl_host(web_acl: WAFV2WebACL, template: NonEC2PiggybackTemplate) -> TargetHost:
    return _hostname_with_hashed_arn("wafv2_webacl", web_acl.name, web_acl.arn, template)


def _cloudfront_distribution_host(
    distribution: CloudFrontDistribution, naming: HostNaming
) -> TargetHost:
    match naming.cloudfront:
        case CloudFrontHostAssignment.account:
            return account_host(naming.account_id)
        case CloudFrontHostAssignment.origin_domain:
            if distribution.origin_domain:
                return TargetHost(distribution.origin_domain)
            return account_host(naming.account_id)
        case CloudFrontHostAssignment.distribution:
            return _hostname_with_hashed_arn(
                "cloudfront_distribution",
                distribution.distribution_id,
                distribution.arn,
                naming.non_ec2,
            )
        case _:
            assert_never(naming.cloudfront)


def _glacier_vault_host(vault: GlacierVault, template: NonEC2PiggybackTemplate) -> TargetHost:
    return _hostname_with_hashed_arn("glacier_vault", vault.name, vault.arn, template)


def _s3_bucket_host(bucket: S3Bucket, template: NonEC2PiggybackTemplate) -> TargetHost:
    return _hostname_with_hashed_arn("s3_bucket", bucket.name, bucket.arn, template)


def _elasticache_node_host(node: ElastiCacheNode, template: NonEC2PiggybackTemplate) -> TargetHost:
    return _hostname_with_hashed_arn("elasticache_cluster", node.node_id, node.arn, template)


def _rds_instance_host(instance: RDSInstance, template: NonEC2PiggybackTemplate) -> TargetHost:
    return _hostname_with_hashed_arn("rds_db", instance.instance_id, instance.arn, template)


def _sns_topic_host(topic: SNSTopic, template: NonEC2PiggybackTemplate) -> TargetHost:
    return _hostname_with_hashed_arn("sns_topic", topic.name, topic.arn, template)


def _lambda_function_host(
    function: LambdaFunction, template: NonEC2PiggybackTemplate
) -> TargetHost:
    return _hostname_with_hashed_arn("lambda_function", function.name, function.arn, template)


def _ecs_cluster_host(cluster: ECSCluster, template: NonEC2PiggybackTemplate) -> TargetHost:
    return _hostname_with_hashed_arn("ecs_cluster", cluster.name, cluster.arn, template)


def _hostname_from_name_and_region(name: str, region: str) -> TargetHost:
    """
    We add the region to the the hostname because resources in different regions might have the
    same names (for example replicated DynamoDB tables).
    """
    return TargetHost(f"{name}_{region}")


def _sanitize_name(name: str) -> str:
    """
    Replace each character that a host name cannot contain with "_".
    """
    return INVALID_HOST_NAME_CHAR.sub("_", name)


def _hash_arn(arn: str) -> str:
    """
    Generate a mostly-unique hash (partial sha256) from an ARN.
    """
    sha = hashlib.sha256(arn.encode("utf-8"), usedforsecurity=False).hexdigest()
    return sha[-PIGGYBACK_HASH_LENGTH:]


def _hostname_with_hashed_arn(
    resource_type: str,
    name: str,
    arn: str,
    template: NonEC2PiggybackTemplate,
) -> TargetHost:
    """
    Given an AWS resource type, a name and an ARN from AWS, create a unique piggyback host name.

    Template:
    LONG: aws_<resource type>_<name>_<ARN hash>
    SHORT: <name>_<ARN hash>
    """

    name = _sanitize_name(name)
    arn_hash = _hash_arn(arn)
    match template:
        case NonEC2PiggybackTemplate.LONG:
            return TargetHost(f"aws_{resource_type}_{name}_{arn_hash}")
        case NonEC2PiggybackTemplate.SHORT:
            return TargetHost(f"{name}_{arn_hash}")
