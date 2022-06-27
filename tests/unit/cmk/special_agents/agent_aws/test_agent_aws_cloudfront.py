#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

import datetime
from typing import Literal

import pytest
from dateutil.tz import tzutc

from cmk.special_agents.agent_aws import AWSConfig, CloudFront, CloudFrontSummary, ResultDistributor

from .agent_aws_fake_clients import FakeCloudwatchClient

PIGGYBACK_HOSTNAME = "giordano-dev-cmk.s3.us-east-1.amazonaws.com"

PAGINATOR_RESULT = {
    "ResponseMetadata": {
        "RequestId": "a771fc6a-bb40-437e-a816-abef183c706f",
        "HTTPStatusCode": 200,
        "HTTPHeaders": {
            "x-amzn-requestid": "a771fc6a-bb40-437e-a816-abef183c706f",
            "content-type": "text/xml",
            "content-length": "5510",
            "date": "Wed, 01 Jun 2022 14:14:35 GMT",
        },
        "RetryAttempts": 0,
    },
    "DistributionList": {
        "Marker": "",
        "MaxItems": 100,
        "IsTruncated": False,
        "Quantity": 2,
        "Items": [
            {
                "Id": "E2RAYOVSSL6ZM3",
                "ARN": "arn:aws:cloudfront::710145618630:distribution/E2RAYOVSSL6ZM3",
                "Status": "Deployed",
                "LastModifiedTime": datetime.datetime(
                    2022, 3, 21, 15, 11, 39, 175000, tzinfo=tzutc()
                ),
                "DomainName": "d29xt669cmrd39.cloudfront.net",
                "Aliases": {"Quantity": 0},
                "Origins": {
                    "Quantity": 1,
                    "Items": [
                        {
                            "Id": "giordano-dev-cmk.s3.us-east-1.amazonaws.com",
                            "DomainName": PIGGYBACK_HOSTNAME,
                            "OriginPath": "/cloudfront",
                            "CustomHeaders": {"Quantity": 0},
                            "S3OriginConfig": {
                                "OriginAccessIdentity": "origin-access-identity/cloudfront/E2I4ASNCOB5LZN"
                            },
                            "ConnectionAttempts": 3,
                            "ConnectionTimeout": 10,
                            "OriginShield": {"Enabled": False},
                        }
                    ],
                },
                "OriginGroups": {"Quantity": 0},
                "DefaultCacheBehavior": {
                    "TargetOriginId": "giordano-dev-cmk.s3.us-east-1.amazonaws.com",
                    "TrustedSigners": {"Enabled": False, "Quantity": 0},
                    "TrustedKeyGroups": {"Enabled": False, "Quantity": 0},
                    "ViewerProtocolPolicy": "allow-all",
                    "AllowedMethods": {
                        "Quantity": 2,
                        "Items": ["HEAD", "GET"],
                        "CachedMethods": {"Quantity": 2, "Items": ["HEAD", "GET"]},
                    },
                    "SmoothStreaming": False,
                    "Compress": True,
                    "LambdaFunctionAssociations": {"Quantity": 0},
                    "FunctionAssociations": {"Quantity": 0},
                    "FieldLevelEncryptionId": "",
                    "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
                },
                "CacheBehaviors": {"Quantity": 0},
                "CustomErrorResponses": {"Quantity": 0},
                "Comment": "",
                "PriceClass": "PriceClass_All",
                "Enabled": True,
                "ViewerCertificate": {
                    "CloudFrontDefaultCertificate": True,
                    "SSLSupportMethod": "vip",
                    "MinimumProtocolVersion": "TLSv1",
                    "CertificateSource": "cloudfront",
                },
                "Restrictions": {"GeoRestriction": {"RestrictionType": "none", "Quantity": 0}},
                "WebACLId": "",
                "HttpVersion": "HTTP2",
                "IsIPV6Enabled": True,
            },
            {
                "Id": "EWN6C0UT7HBX0",
                "ARN": "arn:aws:cloudfront::710145618630:distribution/EWN6C0UT7HBX0",
                "Status": "Deployed",
                "LastModifiedTime": datetime.datetime(
                    2022, 3, 23, 10, 27, 53, 702000, tzinfo=tzutc()
                ),
                "DomainName": "d2pm567xylx0nx.cloudfront.net",
                "Aliases": {"Quantity": 0},
                "Origins": {
                    "Quantity": 1,
                    "Items": [
                        {
                            "Id": "giordano-dev-cmk.s3.us-east-1.amazonaws.com",
                            "DomainName": PIGGYBACK_HOSTNAME,
                            "OriginPath": "/cloudfront2",
                            "CustomHeaders": {"Quantity": 0},
                            "S3OriginConfig": {
                                "OriginAccessIdentity": "origin-access-identity/cloudfront/E2I4ASNCOB5LZN"
                            },
                            "ConnectionAttempts": 3,
                            "ConnectionTimeout": 10,
                            "OriginShield": {"Enabled": False},
                        }
                    ],
                },
                "OriginGroups": {"Quantity": 0},
                "DefaultCacheBehavior": {
                    "TargetOriginId": "giordano-dev-cmk.s3.us-east-1.amazonaws.com",
                    "TrustedSigners": {"Enabled": False, "Quantity": 0},
                    "TrustedKeyGroups": {"Enabled": False, "Quantity": 0},
                    "ViewerProtocolPolicy": "allow-all",
                    "AllowedMethods": {
                        "Quantity": 2,
                        "Items": ["HEAD", "GET"],
                        "CachedMethods": {"Quantity": 2, "Items": ["HEAD", "GET"]},
                    },
                    "SmoothStreaming": False,
                    "Compress": True,
                    "LambdaFunctionAssociations": {"Quantity": 0},
                    "FunctionAssociations": {"Quantity": 0},
                    "FieldLevelEncryptionId": "",
                    "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
                },
                "CacheBehaviors": {"Quantity": 0},
                "CustomErrorResponses": {"Quantity": 0},
                "Comment": "",
                "PriceClass": "PriceClass_All",
                "Enabled": True,
                "ViewerCertificate": {
                    "CloudFrontDefaultCertificate": True,
                    "SSLSupportMethod": "vip",
                    "MinimumProtocolVersion": "TLSv1",
                    "CertificateSource": "cloudfront",
                },
                "Restrictions": {"GeoRestriction": {"RestrictionType": "none", "Quantity": 0}},
                "WebACLId": "",
                "HttpVersion": "HTTP2",
                "IsIPV6Enabled": True,
            },
        ],
    },
}


TAGGING_PAGINATOR_RESULT = {
    "PaginationToken": "",
    "ResourceTagMappingList": [
        {"ResourceARN": "arn:aws:cloudfront::710145618630:distribution/E2RAYOVSSL6ZM3", "Tags": []},
        {
            "ResourceARN": "arn:aws:cloudfront::710145618630:distribution/EWN6C0UT7HBX0",
            "Tags": [
                {"Key": "test-tag-key2", "Value": "test-tag-value2"},
                {"Key": "test-tag-key", "Value": "test-tag-value"},
            ],
        },
    ],
    "ResponseMetadata": {
        "RequestId": "2a732def-b822-4eda-aa21-525b355f4c5d",
        "HTTPStatusCode": 200,
        "HTTPHeaders": {
            "x-amzn-requestid": "2a732def-b822-4eda-aa21-525b355f4c5d",
            "content-type": "application/x-amz-json-1.1",
            "content-length": "323",
            "date": "Wed, 01 Jun 2022 14:30:47 GMT",
        },
        "RetryAttempts": 0,
    },
}


class Paginator:
    def paginate(self, *args, **kwargs):
        yield PAGINATOR_RESULT


class FakeCloudFrontClient:
    def get_paginator(self, operation_name):
        if operation_name == "list_distributions":
            return Paginator()
        raise NotImplementedError


class TaggingPaginator:
    def paginate(self, *args, **kwargs):
        yield TAGGING_PAGINATOR_RESULT


class FakeTaggingClient:
    def get_paginator(self, operation_name):
        if operation_name == "get_resources":
            return TaggingPaginator()
        raise NotImplementedError


@pytest.fixture()
def get_cloudfront_sections():
    def _create_cloudfront_sections(names, tags, assign_to_domain_host: bool):
        region = "us-east-1"
        config = AWSConfig("hostname", [], (None, None))
        config.add_single_service_config("cloudfront_names", names)
        config.add_service_tags("cloudfront_tags", tags)

        fake_cloudfront_client = FakeCloudFrontClient()
        fake_cloudwatch_client = FakeCloudwatchClient()
        fake_tagging_client = FakeTaggingClient()

        cloudfront_summary_distributor = ResultDistributor()

        cloudfront_summary = CloudFrontSummary(
            fake_cloudfront_client,
            fake_tagging_client,
            region,
            config,
            cloudfront_summary_distributor,
        )
        host_assignment: Literal["domain_host", "aws_host"] = (
            "domain_host" if assign_to_domain_host else "aws_host"
        )
        cloudfront = CloudFront(fake_cloudwatch_client, region, config, host_assignment)
        cloudfront_summary_distributor.add(cloudfront)

        return cloudfront_summary, cloudfront

    return _create_cloudfront_sections


cloudfront_params = [
    (None, (None, None), False, ["E2RAYOVSSL6ZM3", "EWN6C0UT7HBX0"]),
    (None, (None, None), True, ["E2RAYOVSSL6ZM3", "EWN6C0UT7HBX0"]),
    (["E2RAYOVSSL6ZM3"], (None, None), False, ["E2RAYOVSSL6ZM3"]),
    (["E2RAYOVSSL6ZM3"], (None, None), True, ["E2RAYOVSSL6ZM3"]),
    (None, ([["test-tag-key"]], [["test-tag-value"]]), False, ["EWN6C0UT7HBX0"]),
    (None, ([["test-tag-key"]], [["test-tag-value"]]), True, ["EWN6C0UT7HBX0"]),
    (None, ([["test-tag-key"]], [["wrong-tag-value"]]), False, []),
    (None, ([["wrong-tag-key"]], [["test-tag-value"]]), False, []),
    (["NONEXISTINGID"], (None, None), False, []),
    (["E2RAYOVSSL6ZM3", "EWN6C0UT7HBX0"], (None, None), False, ["E2RAYOVSSL6ZM3", "EWN6C0UT7HBX0"]),
]


@pytest.mark.parametrize("names, tags, use_piggyback, found_distributions", cloudfront_params)
def test_agent_aws_cloudfront_summary(
    get_cloudfront_sections, names, tags, use_piggyback, found_distributions
):
    cloudfront_summary, _cloudfront = get_cloudfront_sections(names, tags, use_piggyback)
    cloudfront_summary_results = cloudfront_summary.run().results

    assert cloudfront_summary.cache_interval == 300
    assert cloudfront_summary.period == 600
    assert cloudfront_summary.name == "cloudfront_summary"

    if found_distributions:
        assert len(cloudfront_summary_results) == 1
        cloudfront_summary_result = cloudfront_summary_results[0]
        assert cloudfront_summary_result.piggyback_hostname == ""
        assert [e["Id"] for e in cloudfront_summary_result.content] == found_distributions
    else:
        assert len(cloudfront_summary_results) == 0


@pytest.mark.parametrize("names, tags, use_piggyback, found_distributions", cloudfront_params)
def test_agent_aws_cloudfront(
    get_cloudfront_sections, names, tags, use_piggyback, found_distributions
):
    cloudfront_summary, cloudfront = get_cloudfront_sections(names, tags, use_piggyback)
    cloudfront_summary.run()
    cloudfront_results = cloudfront.run().results

    assert cloudfront.cache_interval == 300
    assert cloudfront.period == 600
    assert cloudfront.name == "cloudfront_cloudwatch"

    if found_distributions:
        assert len(cloudfront_results) == 1
        cloudfront_result = cloudfront_results[0]
        assert cloudfront_result.piggyback_hostname == (PIGGYBACK_HOSTNAME if use_piggyback else "")
        assert set(e["Label"] for e in cloudfront_result.content) == set(found_distributions)
        # We are retrieving 6 metrics for each CloudFront distribution
        assert len(cloudfront_result.content) == 6 * len(found_distributions)
    else:
        assert len(cloudfront_results) == 0
