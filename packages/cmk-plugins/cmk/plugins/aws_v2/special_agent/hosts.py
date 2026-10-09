#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The one place that decides which host the data of an AWS resource goes to.

Every section asks target_host for the host of its results. Data about the AWS account
or a region as a whole goes to the source host, the host that runs the special agent.
Some resources get a piggyback host of their own. Each resource type has its own host
name function below.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import assert_never, NewType, overload, Self

from pydantic import BaseModel, Field

from .config import CloudFrontHostAssignment, HostNaming, NamingConvention

TargetHost = NewType("TargetHost", str)

SOURCE_HOST = TargetHost("")
"""The host that runs the special agent. The agent writes no piggyback header for it."""


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
    region: str


# Every resource type except EC2Instance always has a host.
HostedResource = (
    AccountScope
    | EBSAttachment
    | ClassicLoadBalancer
    | LoadBalancerV2
    | DynamoDBTable
    | WAFV2WebACL
    | CloudFrontDistribution
    | GlacierVault
)


@overload
def target_host(resource: EC2Instance, naming: HostNaming) -> TargetHost | None: ...


@overload
def target_host(resource: HostedResource, naming: HostNaming) -> TargetHost: ...


def target_host(resource: EC2Instance | HostedResource, naming: HostNaming) -> TargetHost | None:
    """Decide the host that the data of an AWS resource goes to.

    None means that the EC2 instance has no host name. The agent then skips it.
    """
    match resource:
        case AccountScope():
            return SOURCE_HOST
        case EC2Instance():
            return _ec2_instance_host(resource, naming.ec2)
        case EBSAttachment():
            return _ebs_attachment_host(resource)
        case ClassicLoadBalancer():
            return _classic_load_balancer_host(resource)
        case LoadBalancerV2():
            return _load_balancer_v2_host(resource)
        case DynamoDBTable():
            return _dynamodb_table_host(resource)
        case WAFV2WebACL():
            return _wafv2_web_acl_host(resource)
        case CloudFrontDistribution():
            return _cloudfront_distribution_host(resource, naming.cloudfront)
        case GlacierVault():
            return _glacier_vault_host(resource)
        case _:
            assert_never(resource)


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


def _ebs_attachment_host(attachment: EBSAttachment) -> TargetHost:
    return SOURCE_HOST if attachment.instance_host is None else attachment.instance_host


def _classic_load_balancer_host(load_balancer: ClassicLoadBalancer) -> TargetHost:
    return TargetHost(load_balancer.dns_name)


def _load_balancer_v2_host(load_balancer: LoadBalancerV2) -> TargetHost:
    return TargetHost(load_balancer.dns_name)


def _dynamodb_table_host(table: DynamoDBTable) -> TargetHost:
    return _hostname_from_name_and_region(table.name, table.region)


def _wafv2_web_acl_host(web_acl: WAFV2WebACL) -> TargetHost:
    return _hostname_from_name_and_region(web_acl.name, web_acl.region)


def _cloudfront_distribution_host(
    distribution: CloudFrontDistribution, assignment: CloudFrontHostAssignment
) -> TargetHost:
    if assignment == "domain_host" and distribution.origin_domain:
        return TargetHost(distribution.origin_domain)
    return SOURCE_HOST


def _glacier_vault_host(vault: GlacierVault) -> TargetHost:
    return _hostname_from_name_and_region(vault.name, vault.region)


def _hostname_from_name_and_region(name: str, region: str) -> TargetHost:
    """
    We add the region to the the hostname because resources in different regions might have the
    same names (for example replicated DynamoDB tables).
    """
    return TargetHost(f"{name}_{region}")
