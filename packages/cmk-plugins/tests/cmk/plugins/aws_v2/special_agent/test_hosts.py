#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.aws_v2.special_agent.config import (
    CloudFrontHostAssignment,
    HostNaming,
    NamingConvention,
    NonEC2PiggybackTemplate,
)
from cmk.plugins.aws_v2.special_agent.hosts import (
    AccountScope,
    ClassicLoadBalancer,
    CloudFrontDistribution,
    DynamoDBTable,
    EBSAttachment,
    ec2_instance_hosts,
    ECSCluster,
    ElastiCacheNode,
    GlacierVault,
    HostedResource,
    LambdaFunction,
    LoadBalancerV2,
    PiggybackResource,
    RDSInstance,
    S3Bucket,
    SNSTopic,
    target_host,
    TargetHost,
    WAFV2WebACL,
)

DEFAULT_NAMING = HostNaming(
    ec2=NamingConvention.ip_region_instance,
    non_ec2=NonEC2PiggybackTemplate.LONG,
    cloudfront=CloudFrontHostAssignment.account,
    account="333333333333",
)
DOMAIN_HOST_NAMING = HostNaming(
    ec2=NamingConvention.ip_region_instance,
    non_ec2=NonEC2PiggybackTemplate.LONG,
    cloudfront=CloudFrontHostAssignment.origin_domain,
    account="333333333333",
)

INSTANCE = {
    "InstanceId": "i-0abc",
    "PrivateIpAddress": "10.0.0.1",
    "PrivateDnsName": "ip-10-0-0-1.ec2.internal",
}


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
    naming = HostNaming(
        ec2=convention,
        non_ec2=NonEC2PiggybackTemplate.LONG,
        cloudfront=CloudFrontHostAssignment.account,
    )

    assert list(ec2_instance_hosts([INSTANCE], "eu-central-1", naming)) == [(expected, INSTANCE)]


@pytest.mark.parametrize(
    ("convention", "instance"),
    [
        pytest.param(
            NamingConvention.private_dns_name,
            {"InstanceId": "i-0abc", "PrivateIpAddress": "10.0.0.1"},
            id="no dns name",
        ),
        pytest.param(
            NamingConvention.private_dns_name,
            {"InstanceId": "i-0abc", "PrivateIpAddress": "10.0.0.1", "PrivateDnsName": ""},
            id="empty dns name",
        ),
        pytest.param(
            NamingConvention.ip_region_instance,
            {"InstanceId": "i-0abc", "PrivateDnsName": "ip-10-0-0-1.ec2.internal"},
            id="no ip address",
        ),
    ],
)
def test_ec2_instance_without_a_name_has_no_host(
    convention: NamingConvention, instance: Mapping[str, object]
) -> None:
    naming = HostNaming(
        ec2=convention,
        non_ec2=NonEC2PiggybackTemplate.LONG,
        cloudfront=CloudFrontHostAssignment.account,
    )

    assert not list(ec2_instance_hosts([instance], "eu-central-1", naming))


@pytest.mark.parametrize(
    ("resource", "expected"),
    [
        pytest.param(
            ClassicLoadBalancer(
                "elb", "arn:aws:elasticloadbalancing:eu-central-1:123456789012:loadbalancer/elb"
            ),
            "aws_elasticloadbalancing_loadbalancer_elb_3a50c4d7",
            id="classic load balancer",
        ),
        pytest.param(
            LoadBalancerV2(
                "alb",
                "arn:aws:elasticloadbalancing:eu-central-1:123456789012:loadbalancer/app/alb/50dc6c495c0c9188",
            ),
            "aws_elasticloadbalancing_loadbalancer_alb_48da024d",
            id="load balancer v2",
        ),
        pytest.param(
            DynamoDBTable("users", "arn:aws:dynamodb:eu-central-1:111122223333:table/users"),
            "aws_dynamodb_table_users_a93630d8",
            id="dynamodb table",
        ),
        pytest.param(
            WAFV2WebACL(
                "api-protection",
                "arn:aws:wafv2:eu-central-1:111122223333:regional/webacl/api-protection/a1b2c3d4-5678-90ab-cdef-111122223333",
            ),
            "aws_wafv2_webacl_api-protection_a8d53eb5",
            id="web acl",
        ),
        pytest.param(
            GlacierVault("my-vault", "arn:aws:glacier:eu-central-1:123456789012:vaults/my-vault"),
            "aws_glacier_vault_my-vault_a87a2b00",
            id="glacier vault",
        ),
        pytest.param(
            S3Bucket("bucket", "arn:aws:s3:::bucket"),
            "aws_s3_bucket_bucket_5c001db1",
            id="s3 bucket",
        ),
        pytest.param(SNSTopic("topic", "eu-central-1"), "topic_eu-central-1", id="sns topic"),
        pytest.param(
            LambdaFunction(
                "function", "arn:aws:lambda:eu-central-1:123456789012:function:function"
            ),
            "aws_lambda_function_function_6086769b",
            id="lambda function",
        ),
        pytest.param(
            ECSCluster("cluster", "eu-central-1"), "cluster_eu-central-1", id="ecs cluster"
        ),
    ],
)
def test_resource_goes_to_a_host_of_its_own(resource: PiggybackResource, expected: str) -> None:
    assert target_host(resource, DEFAULT_NAMING) == expected


def test_sns_topics_with_the_same_name_in_two_regions_go_to_two_hosts() -> None:
    assert target_host(SNSTopic("topic", "eu-central-1"), DEFAULT_NAMING) != target_host(
        SNSTopic("topic", "us-east-1"), DEFAULT_NAMING
    )


def test_ecs_clusters_with_the_same_name_in_two_regions_go_to_two_hosts() -> None:
    assert target_host(ECSCluster("cluster", "eu-central-1"), DEFAULT_NAMING) != target_host(
        ECSCluster("cluster", "us-east-1"), DEFAULT_NAMING
    )


@pytest.mark.parametrize(
    "other_arn",
    [
        pytest.param(
            "arn:aws:lambda:us-east-1:123456789012:function:function", id="another region"
        ),
        pytest.param(
            "arn:aws:lambda:eu-central-1:210987654321:function:function", id="another account"
        ),
    ],
)
def test_lambda_functions_with_the_same_name_and_another_arn_go_to_two_hosts(
    other_arn: str,
) -> None:
    function = LambdaFunction(
        "function", "arn:aws:lambda:eu-central-1:123456789012:function:function"
    )

    assert target_host(function, DEFAULT_NAMING) != target_host(
        LambdaFunction("function", other_arn), DEFAULT_NAMING
    )


def test_regional_and_global_web_acls_with_the_same_name_go_to_two_hosts() -> None:
    regional = WAFV2WebACL(
        "acl", "arn:aws:wafv2:us-east-1:123456789012:regional/webacl/acl/a1b2c3d4"
    )
    global_ = WAFV2WebACL("acl", "arn:aws:wafv2:us-east-1:123456789012:global/webacl/acl/e5f6a7b8")

    assert target_host(regional, DEFAULT_NAMING) != target_host(global_, DEFAULT_NAMING)


def test_lambda_function_host_follows_the_short_template() -> None:
    naming = HostNaming(
        ec2=NamingConvention.ip_region_instance,
        non_ec2=NonEC2PiggybackTemplate.SHORT,
        cloudfront=CloudFrontHostAssignment.account,
    )
    function = LambdaFunction(
        "function", "arn:aws:lambda:eu-central-1:123456789012:function:function"
    )

    assert target_host(function, naming) == "function_6086769b"


def test_ebs_attachment_goes_to_the_host_of_its_monitored_instance() -> None:
    attachment = EBSAttachment(TargetHost("instance-host"))

    assert target_host(attachment, DEFAULT_NAMING) == "instance-host"


def test_cloudfront_distribution_goes_to_its_origin_domain_host_when_assigned() -> None:
    distribution = CloudFrontDistribution(
        "E2RAYOVSSL6ZM3",
        "origin.example.com",
        "arn:aws:cloudfront::111122223333:distribution/E2RAYOVSSL6ZM3",
    )

    assert target_host(distribution, DOMAIN_HOST_NAMING) == "origin.example.com"


def test_cloudfront_distribution_goes_to_its_own_host_when_assigned() -> None:
    distribution = CloudFrontDistribution(
        "E2RAYOVSSL6ZM3",
        "origin.example.com",
        "arn:aws:cloudfront::111122223333:distribution/E2RAYOVSSL6ZM3",
    )
    naming = HostNaming(
        ec2=NamingConvention.ip_region_instance,
        non_ec2=NonEC2PiggybackTemplate.LONG,
        cloudfront=CloudFrontHostAssignment.distribution,
    )

    assert (
        target_host(distribution, naming) == "aws_cloudfront_distribution_E2RAYOVSSL6ZM3_348005b8"
    )


@pytest.mark.parametrize(
    "origin_domain", [pytest.param(None, id="none"), pytest.param("", id="empty")]
)
def test_cloudfront_distribution_without_origin_goes_to_the_account_host(
    origin_domain: str | None,
) -> None:
    distribution = CloudFrontDistribution(
        "E2RAYOVSSL6ZM3",
        origin_domain,
        "arn:aws:cloudfront::111122223333:distribution/E2RAYOVSSL6ZM3",
    )

    assert target_host(distribution, DOMAIN_HOST_NAMING) == "333333333333"


@pytest.mark.parametrize(
    ("resource", "cloudfront"),
    [
        pytest.param(AccountScope(), CloudFrontHostAssignment.account, id="account"),
        pytest.param(
            EBSAttachment(None),
            CloudFrontHostAssignment.account,
            id="ebs attached to unmonitored instance",
        ),
        pytest.param(
            CloudFrontDistribution(
                "E2RAYOVSSL6ZM3",
                "origin.example.com",
                "arn:aws:cloudfront::111122223333:distribution/E2RAYOVSSL6ZM3",
            ),
            CloudFrontHostAssignment.account,
            id="cloudfront assigned to aws host",
        ),
        pytest.param(
            CloudFrontDistribution(
                "E2RAYOVSSL6ZM3",
                None,
                "arn:aws:cloudfront::111122223333:distribution/E2RAYOVSSL6ZM3",
            ),
            CloudFrontHostAssignment.origin_domain,
            id="cloudfront without origin",
        ),
    ],
)
def test_account_data_goes_to_the_account_host(
    resource: HostedResource, cloudfront: CloudFrontHostAssignment
) -> None:
    naming = HostNaming(
        ec2=NamingConvention.ip_region_instance,
        non_ec2=NonEC2PiggybackTemplate.LONG,
        cloudfront=cloudfront,
        account="333333333333",
    )

    assert target_host(resource, naming) == "333333333333"


def test_elasticache_node_goes_to_a_host_per_node() -> None:
    node = ElastiCacheNode("test-redis-cluster-3-0001-001", "eu-central-1")

    assert target_host(node, DEFAULT_NAMING) == "test-redis-cluster-3-0001-001_eu-central-1"


def test_elasticache_nodes_with_the_same_id_in_two_regions_go_to_two_hosts() -> None:
    assert target_host(ElastiCacheNode("node", "eu-central-1"), DEFAULT_NAMING) != target_host(
        ElastiCacheNode("node", "us-east-1"), DEFAULT_NAMING
    )


def test_rds_instance_goes_to_a_host_per_instance() -> None:
    instance = RDSInstance("mydb", "eu-central-1")

    assert target_host(instance, DEFAULT_NAMING) == "mydb_eu-central-1"


def test_rds_instances_with_the_same_id_in_two_regions_go_to_two_hosts() -> None:
    assert target_host(RDSInstance("mydb", "eu-central-1"), DEFAULT_NAMING) != target_host(
        RDSInstance("mydb", "us-east-1"), DEFAULT_NAMING
    )
