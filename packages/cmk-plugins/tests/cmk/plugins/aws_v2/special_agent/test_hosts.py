#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.aws_v2.special_agent.config import HostNaming, NamingConvention
from cmk.plugins.aws_v2.special_agent.hosts import (
    AccountScope,
    ClassicLoadBalancer,
    CloudFrontDistribution,
    DynamoDBTable,
    EBSAttachment,
    EC2Instance,
    GlacierVault,
    HostedResource,
    LoadBalancerV2,
    SOURCE_HOST,
    target_host,
    TargetHost,
    WAFV2WebACL,
)

DEFAULT_NAMING = HostNaming(ec2=NamingConvention.ip_region_instance, cloudfront="aws_host")
DOMAIN_HOST_NAMING = HostNaming(ec2=NamingConvention.ip_region_instance, cloudfront="domain_host")

INSTANCE = EC2Instance(
    instance_id="i-0abc",
    private_ip_address="10.0.0.1",
    private_dns_name="ip-10-0-0-1.ec2.internal",
    region="eu-central-1",
)


@pytest.mark.parametrize(
    ("convention", "expected"),
    [
        pytest.param(
            NamingConvention.ip_region_instance,
            "10.0.0.1-eu-central-1-i-0abc",
            id="ip region instance",
        ),
        pytest.param(
            NamingConvention.private_dns_name, "ip-10-0-0-1.ec2.internal", id="private dns name"
        ),
    ],
)
def test_ec2_instance_host_follows_the_naming_convention(
    convention: NamingConvention, expected: str
) -> None:
    naming = HostNaming(ec2=convention, cloudfront="aws_host")

    assert target_host(INSTANCE, naming) == expected


@pytest.mark.parametrize(
    ("convention", "instance"),
    [
        pytest.param(
            NamingConvention.private_dns_name,
            EC2Instance("i-0abc", "10.0.0.1", None, "eu-central-1"),
            id="no dns name",
        ),
        pytest.param(
            NamingConvention.private_dns_name,
            EC2Instance("i-0abc", "10.0.0.1", "", "eu-central-1"),
            id="empty dns name",
        ),
        pytest.param(
            NamingConvention.ip_region_instance,
            EC2Instance("i-0abc", None, "ip-10-0-0-1.ec2.internal", "eu-central-1"),
            id="no ip address",
        ),
    ],
)
def test_ec2_instance_without_a_name_has_no_host(
    convention: NamingConvention, instance: EC2Instance
) -> None:
    naming = HostNaming(ec2=convention, cloudfront="aws_host")

    assert target_host(instance, naming) is None


@pytest.mark.parametrize(
    ("resource", "expected"),
    [
        pytest.param(
            ClassicLoadBalancer("elb.example.com"), "elb.example.com", id="classic load balancer"
        ),
        pytest.param(LoadBalancerV2("alb.example.com"), "alb.example.com", id="load balancer v2"),
        pytest.param(
            DynamoDBTable("users", "eu-central-1"), "users_eu-central-1", id="dynamodb table"
        ),
        pytest.param(WAFV2WebACL("acl", "eu-central-1"), "acl_eu-central-1", id="regional web acl"),
        pytest.param(WAFV2WebACL("acl", "CloudFront"), "acl_CloudFront", id="cloudfront web acl"),
        pytest.param(
            GlacierVault("vault", "eu-central-1"), "vault_eu-central-1", id="glacier vault"
        ),
    ],
)
def test_resource_goes_to_a_host_of_its_own(resource: HostedResource, expected: str) -> None:
    assert target_host(resource, DEFAULT_NAMING) == expected


def test_ebs_attachment_goes_to_the_host_of_its_monitored_instance() -> None:
    attachment = EBSAttachment(TargetHost("instance-host"))

    assert target_host(attachment, DEFAULT_NAMING) == "instance-host"


@pytest.mark.parametrize(
    "resource",
    [
        pytest.param(AccountScope(), id="account"),
        pytest.param(EBSAttachment(None), id="ebs attached to unmonitored instance"),
        pytest.param(
            CloudFrontDistribution("origin.example.com"), id="cloudfront assigned to aws host"
        ),
    ],
)
def test_resource_goes_to_the_source_host(resource: HostedResource) -> None:
    assert target_host(resource, DEFAULT_NAMING) == SOURCE_HOST


def test_cloudfront_distribution_goes_to_its_origin_domain_host_when_assigned() -> None:
    distribution = CloudFrontDistribution("origin.example.com")

    assert target_host(distribution, DOMAIN_HOST_NAMING) == "origin.example.com"


@pytest.mark.parametrize(
    "origin_domain", [pytest.param(None, id="none"), pytest.param("", id="empty")]
)
def test_cloudfront_distribution_without_origin_goes_to_the_source_host(
    origin_domain: str | None,
) -> None:
    distribution = CloudFrontDistribution(origin_domain)

    assert target_host(distribution, DOMAIN_HOST_NAMING) == SOURCE_HOST
