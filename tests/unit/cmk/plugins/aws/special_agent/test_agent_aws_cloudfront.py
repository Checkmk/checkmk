#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import datetime
from argparse import Namespace as Args
from collections.abc import Sequence
from typing import Literal, Protocol

import pytest
from dateutil.tz import tzutc

from cmk.plugins.aws.special_agent.agent_aws import (
    AWSConfig,
    CloudFront,
    CloudFrontSummary,
    NamingConvention,
    OverallTags,
    ResultDistributor,
    TagsImportPatternOption,
    TagsOption,
)

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


CloudFrontSectionsOut = tuple[CloudFrontSummary, CloudFront]


class CloudFrontSections(Protocol):
    def __call__(
        self,
        names: object | None,
        tags: OverallTags,
        assign_to_domain_host: bool,
        tag_import: TagsOption = TagsImportPatternOption.import_all,
    ) -> CloudFrontSectionsOut: ...


@pytest.fixture()
def get_cloudfront_sections() -> CloudFrontSections:
    def _create_cloudfront_sections(
        names: object | None,
        tags: OverallTags,
        assign_to_domain_host: bool,
        tag_import: TagsOption = TagsImportPatternOption.import_all,
    ) -> CloudFrontSectionsOut:
        region = "us-east-1"
        config = AWSConfig(
            "hostname", Args(), ([], []), NamingConvention.ip_region_instance, tag_import
        )
        config.add_single_service_config("cloudfront_names", names)
        config.add_service_tags("cloudfront_tags", tags)

        fake_cloudfront_client = FakeCloudFrontClient()
        fake_cloudwatch_client = FakeCloudwatchClient()
        fake_tagging_client = FakeTaggingClient()

        distributor = ResultDistributor()

        # TODO: FakeCloudFrontClient shoud actually subclass CloudFrontClient, etc.
        cloudfront_summary = CloudFrontSummary(
            fake_cloudfront_client,  # type: ignore[arg-type]
            fake_tagging_client,  # type: ignore[arg-type]
            region,
            config,
            distributor,
        )
        host_assignment: Literal["domain_host", "aws_host"] = (
            "domain_host" if assign_to_domain_host else "aws_host"
        )
        cloudfront = CloudFront(fake_cloudwatch_client, region, config, host_assignment)  # type: ignore[arg-type]
        distributor.add(cloudfront_summary.name, cloudfront)

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
    get_cloudfront_sections: CloudFrontSections,
    names: Sequence[str] | None,
    tags: OverallTags,
    use_piggyback: bool,
    found_distributions: Sequence[str],
) -> None:
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
    get_cloudfront_sections: CloudFrontSections,
    names: Sequence[str] | None,
    tags: OverallTags,
    use_piggyback: bool,
    found_distributions: Sequence[str],
) -> None:
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
        assert {e["Label"] for e in cloudfront_result.content} == set(found_distributions)
        # We are retrieving 6 metrics for each CloudFront distribution
        assert len(cloudfront_result.content) == 6 * len(found_distributions)
    else:
        assert len(cloudfront_results) == 0


@pytest.mark.parametrize(
    "tag_import, expected_tags",
    [
        (
            TagsImportPatternOption.import_all,
            {
                "arn:aws:cloudfront::710145618630:distribution/E2RAYOVSSL6ZM3": [],
                "arn:aws:cloudfront::710145618630:distribution/EWN6C0UT7HBX0": [
                    "test-tag-key2",
                    "test-tag-key",
                ],
            },
        ),
        (
            r".*2$",
            {
                "arn:aws:cloudfront::710145618630:distribution/E2RAYOVSSL6ZM3": [],
                "arn:aws:cloudfront::710145618630:distribution/EWN6C0UT7HBX0": ["test-tag-key2"],
            },
        ),
        (
            TagsImportPatternOption.ignore_all,
            {
                "arn:aws:cloudfront::710145618630:distribution/E2RAYOVSSL6ZM3": [],
                "arn:aws:cloudfront::710145618630:distribution/EWN6C0UT7HBX0": [],
            },
        ),
    ],
)
def test_agent_aws_cloudfront_summary_filters_tags(
    get_cloudfront_sections: CloudFrontSections,
    tag_import: TagsOption,
    expected_tags: dict[str, Sequence[str]],
) -> None:
    cloudfront_summary, _cloudfront = get_cloudfront_sections(None, (None, None), False, tag_import)
    cloudfront_summary_results = cloudfront_summary.run().results
    cloudfront_summary_result = cloudfront_summary_results[0]

    for result in cloudfront_summary_result.content:
        assert list(result["TagsForCmkLabels"].keys()) == expected_tags[result["ARN"]]
