#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from argparse import Namespace as Args
from collections.abc import Mapping, Sequence
from datetime import datetime as dt
from types import SimpleNamespace
from typing import Protocol

import pytest

from cmk.plugins.aws_v2.special_agent.config import (
    AWSConfig,
    NamingConvention,
    NonEC2PiggybackTemplate,
    OverallTags,
    TagsImportPatternOption,
    TagsOption,
)
from cmk.plugins.aws_v2.special_agent.hosts import TargetHost

# Needed to monkeypatch NOW in the s3 module
from cmk.plugins.aws_v2.special_agent.sections import s3 as s3_module
from cmk.plugins.aws_v2.special_agent.sections.core import ResultDistributor
from cmk.plugins.aws_v2.special_agent.sections.s3 import (
    S3,
    S3Bucket,
    S3BucketHelper,
    S3Limits,
    S3Requests,
    S3Summary,
)

from .agent_aws_fake_clients import FakeCloudwatchClient, S3BucketTaggingIB, S3ListBucketsIB

ACCOUNT_HOST = TargetHost("aws_account_123456789012")
BUCKET_HOSTS = {
    "Name-0": TargetHost("aws_s3_bucket_Name-0_38ec975c"),
    "Name-1": TargetHost("aws_s3_bucket_Name-1_b382224c"),
    "Name-2": TargetHost("aws_s3_bucket_Name-2_89ce0a4c"),
}


class FakeS3Client:
    def list_buckets(self, MaxBuckets: int = 10000) -> Mapping[str, object]:  # noqa: ARG002
        return {
            "Buckets": S3ListBucketsIB.create_instances(amount=4),
            "Owner": {
                "DisplayName": "string",
                "ID": "string",
            },
        }

    def get_bucket_location(self, Bucket: str = "") -> Mapping[str, object]:
        if Bucket in ["Name-0", "Name-1", "Name-2"]:
            return {
                "LocationConstraint": "region",
            }
        return {}

    def get_bucket_tagging(self, Bucket: str = "") -> Mapping[str, object]:
        if Bucket == "Name-0":
            return {
                "TagSet": S3BucketTaggingIB.create_instances(amount=1),
            }
        if Bucket == "Name-1":
            return {
                "TagSet": S3BucketTaggingIB.create_instances(amount=2),
            }
        return {}


S3Sections = tuple[S3Limits, S3Summary, S3, S3Bucket, S3Requests]


class CreateS3Sections(Protocol):
    def __call__(
        self,
        names: object | None = None,
        tags: OverallTags = (None, None),
        tag_import: TagsOption = TagsImportPatternOption.import_all,
        partition: str = "aws",
    ) -> S3Sections: ...


class FakeEmptyS3Client:
    def __init__(self) -> None:
        self.bucket_listings = 0

    def list_buckets(
        self,
        MaxBuckets: int | None = None,  # noqa: ARG002
        ContinuationToken: str | None = None,  # noqa: ARG002
    ) -> Mapping[str, object]:
        self.bucket_listings += 1
        return {"Buckets": []}


def test_s3_summary_does_not_list_buckets_again_when_limits_found_none() -> None:
    config = AWSConfig(
        "hostname",
        Args(),
        ([], []),
        NamingConvention.ip_region_instance,
        NonEC2PiggybackTemplate.LONG,
    ).for_account("123456789012")
    config.add_single_service_config("s3_names", None)
    config.add_service_tags("s3_tags", (None, None))
    client = FakeEmptyS3Client()
    distributor = ResultDistributor()
    s3_limits = S3Limits(client, "region", config, distributor)
    s3_summary = S3Summary(client, "region", config, distributor)
    distributor.add(s3_limits.name, s3_summary)

    s3_limits.run()
    s3_summary.run()

    assert client.bucket_listings == 1


@pytest.fixture()
def get_s3_sections(monkeypatch: pytest.MonkeyPatch) -> CreateS3Sections:
    def _create_s3_sections(
        names: object | None = None,
        tags: OverallTags = (None, None),
        tag_import: TagsOption = TagsImportPatternOption.import_all,
        partition: str = "aws",
    ) -> S3Sections:
        # on_time is somehow not feeded from here to S3Limits, so use monkey patch...
        monkeypatch.setattr(
            s3_module, "NOW", dt.strptime("2020-09-28 15:30 UTC", "%Y-%m-%d %H:%M %Z")
        )

        region = "region"
        config = AWSConfig(
            "hostname",
            Args(),
            ([], []),
            NamingConvention.ip_region_instance,
            NonEC2PiggybackTemplate.LONG,
            tag_import,
        ).for_account("123456789012")
        config.add_single_service_config("s3_names", names)
        config.add_service_tags("s3_tags", tags)

        fake_s3_client = FakeS3Client()
        fake_cloudwatch_client = FakeCloudwatchClient()
        fake_cloudwatch_client.meta = SimpleNamespace(partition=partition)

        distributor = ResultDistributor()

        # TODO: FakeS3Client shoud actually subclass S3Client, etc.
        s3_limits = S3Limits(fake_s3_client, region, config, distributor)
        s3_summary = S3Summary(fake_s3_client, region, config, distributor)
        s3 = S3(fake_cloudwatch_client, region, config, distributor)
        s3_bucket = S3Bucket(fake_cloudwatch_client, region, config)
        s3_requests = S3Requests(fake_cloudwatch_client, region, config)

        distributor.add(s3_limits.name, s3_summary)
        distributor.add(s3_summary.name, s3)
        distributor.add(s3.name, s3_bucket)
        distributor.add(s3_summary.name, s3_requests)
        return s3_limits, s3_summary, s3, s3_bucket, s3_requests

    return _create_s3_sections


s3_params = [
    (None, (None, None), 3),
    (["Name-0"], (None, None), 1),
    (["Name-0", "Name-1"], (None, None), 2),
    (["Name-0", "Name-1", "Name-2"], (None, None), 3),
    (["Name-0", "Name-1", "Name-2", "string4"], (None, None), 3),
    (["Name-0", "Name-1", "Name-2", "FOOBAR"], (None, None), 3),
    (["Name-0"], (["Key-0"], ["Value-0"]), 1),
    (["Name-0", "Name-1"], (["Key-0"], ["Value-0"]), 2),
    (["Name-0", "Name-1", "Name-2"], (["Key-0"], ["Value-0"]), 3),
    (["Name-0", "Name-1", "Name-2", "string4"], (["Key-0"], ["Value-0"]), 3),
    (["Name-0", "Name-1", "Name-2", "FOOBAR"], (["Key-0"], ["Value-0"]), 3),
    (None, (["Key-1"], ["Value-0"]), 0),
    (None, (["Key-1"], ["Value-1"]), 1),
    (None, (["Key-0"], ["Value-0"]), 2),
    (None, (["Key-0", "Key-0"], ["Value-0", "Value-1"]), 2),
    (None, (["Key-0", "Key-0"], ["Value-0", "Value-1"]), 2),
]


@pytest.mark.parametrize("names,tags,amount_buckets", s3_params)
def test_agent_aws_s3_limits(
    get_s3_sections: CreateS3Sections,
    names: Sequence[str] | None,
    tags: OverallTags,
    amount_buckets: int,  # noqa: ARG001
) -> None:
    s3_limits, _s3_summary, _s3, _s3_bucket, _s3_requests = get_s3_sections(names, tags)
    s3_limits_results = s3_limits.run().results

    assert s3_limits.name == "s3_limits"

    assert len(s3_limits_results) == 1

    s3_limits_result = s3_limits_results[0]
    assert s3_limits_result.piggyback_hostname == ACCOUNT_HOST
    assert len(s3_limits_result.content) == 1

    s3_limits_content = s3_limits_result.content[0]
    assert s3_limits_content.key == "buckets"
    assert s3_limits_content.title == "Buckets"
    assert s3_limits_content.limit == 100
    assert s3_limits_content.amount == 4


@pytest.mark.parametrize("names,tags,amount_buckets", s3_params)
def test_agent_aws_s3_summary(
    get_s3_sections: CreateS3Sections,
    names: Sequence[str] | None,
    tags: OverallTags,
    amount_buckets: int,
) -> None:
    s3_limits, s3_summary, _s3, _s3_bucket, _s3_requests = get_s3_sections(names, tags)
    s3_limits.run()
    s3_summary_results = s3_summary.run().results

    assert s3_summary.name == "s3_summary"

    if amount_buckets:
        assert len(s3_summary_results) == 1
        s3_summary_result = s3_summary_results[0]
        assert s3_summary_result.piggyback_hostname == ACCOUNT_HOST
        assert len(s3_summary_result.content) == amount_buckets
    else:
        assert not s3_summary_results


@pytest.mark.parametrize("names,tags,amount_buckets", s3_params)
def test_agent_aws_s3(
    get_s3_sections: CreateS3Sections,
    names: Sequence[str] | None,
    tags: OverallTags,
    amount_buckets: int,
) -> None:
    s3_limits, s3_summary, s3, _s3_bucket, _s3_requests = get_s3_sections(names, tags)
    _s3_limits_results = s3_limits.run().results
    _s3_summary_results = s3_summary.run().results
    s3_results = s3.run().results
    assert s3.name == "s3"

    if amount_buckets:
        assert len(s3_results) == 1
        s3_result = s3_results[0]
        assert s3_result.piggyback_hostname == ACCOUNT_HOST

        # Y (len results) == 4 (metrics) * X (buckets)
        assert len(s3_result.content) == 4 * amount_buckets
        for row in s3_result.content:
            if row.get("Name") in ["Name-0", "Name-1", "Name-2"]:
                assert row.get("LocationConstraint") == "region"
            assert "Tagging" in row


@pytest.mark.parametrize("names,tags,amount_buckets", s3_params)
def test_agent_aws_s3_requests(
    get_s3_sections: CreateS3Sections,
    names: Sequence[str] | None,
    tags: OverallTags,
    amount_buckets: int,
) -> None:
    s3_limits, s3_summary, _s3, _s3_bucket, s3_requests = get_s3_sections(names, tags)
    _s3_limits_results = s3_limits.run().results
    _s3_summary_results = s3_summary.run().results
    s3_requests_results = s3_requests.run().results

    assert s3_requests.cache_interval == 300
    assert s3_requests.period == 600
    assert s3_requests.name == "s3_requests"

    assert len(s3_requests_results) == amount_buckets
    for s3_requests_result in s3_requests_results:
        # 16 metrics per bucket
        assert len(s3_requests_result.content) == 16
        for row in s3_requests_result.content:
            assert s3_requests_result.piggyback_hostname == BUCKET_HOSTS[row["Label"]]
            if row.get("Name") in ["Name-0", "Name-1", "Name-2"]:
                assert row.get("LocationConstraint") == "region"
            assert "Tagging" in row


@pytest.mark.parametrize("names,tags,amount_buckets", s3_params)
def test_agent_aws_s3_summary_without_limits(
    get_s3_sections: CreateS3Sections,
    names: Sequence[str] | None,
    tags: OverallTags,
    amount_buckets: int,
) -> None:
    _s3_limits, s3_summary, _s3, _s3_bucket, _s3_requests = get_s3_sections(names, tags)
    s3_summary_results = s3_summary.run().results

    assert s3_summary.name == "s3_summary"

    if amount_buckets:
        assert len(s3_summary_results) == 1
        s3_summary_result = s3_summary_results[0]
        assert s3_summary_result.piggyback_hostname == ACCOUNT_HOST
        assert len(s3_summary_result.content) == amount_buckets
        assert "Tagging" in s3_summary_result.content[0]
    else:
        assert not s3_summary_results


@pytest.mark.parametrize("names,tags,amount_buckets", s3_params)
def test_agent_aws_s3_without_limits(
    get_s3_sections: CreateS3Sections,
    names: Sequence[str] | None,
    tags: OverallTags,
    amount_buckets: int,
) -> None:
    _s3_limits, s3_summary, s3, _s3_bucket, _s3_requests = get_s3_sections(names, tags)
    s3_summary.run()
    s3_results = s3.run().results

    assert s3.name == "s3"

    if amount_buckets:
        assert len(s3_results) == 1
        s3_result = s3_results[0]
        assert s3_result.piggyback_hostname == ACCOUNT_HOST

        # Y (len results) == 4 (metrics) * X (buckets)
        assert len(s3_result.content) == 4 * amount_buckets
        for row in s3_result.content:
            if row.get("Name") in ["Name-0", "Name-1", "Name-2"]:
                assert row.get("LocationConstraint") == "region"
            assert "Tagging" in row


@pytest.mark.parametrize("names,tags,amount_buckets", s3_params)
def test_agent_aws_s3_requests_without_limits(
    get_s3_sections: CreateS3Sections,
    names: Sequence[str] | None,
    tags: OverallTags,
    amount_buckets: int,
) -> None:
    s3_limits, s3_summary, _s3, _s3_bucket, s3_requests = get_s3_sections(names, tags)
    s3_summary.run()
    s3_requests_results = s3_requests.run().results

    assert s3_requests.cache_interval == 300
    assert s3_requests.period == 600
    assert s3_requests.name == "s3_requests"

    assert s3_limits.cache_interval == 55800
    assert s3_limits.period == 172800

    assert len(s3_requests_results) == amount_buckets
    for s3_requests_result in s3_requests_results:
        # 16 metrics per bucket
        assert len(s3_requests_result.content) == 16
        for row in s3_requests_result.content:
            assert s3_requests_result.piggyback_hostname == BUCKET_HOSTS[row["Label"]]
            if row.get("Name") in ["Name-0", "Name-1", "Name-2"]:
                assert row.get("LocationConstraint") == "region"
            assert "Tagging" in row


@pytest.mark.parametrize(
    "tag_import, expected_tags",
    [
        (
            TagsImportPatternOption.import_all,
            {"Name-0": ["Key-0"], "Name-1": ["Key-0", "Key-1"]},
        ),
        (r".*-1$", {"Name-1": ["Key-1"]}),
        (TagsImportPatternOption.ignore_all, {}),
    ],
)
def test_agent_aws_s3_filters_tags(
    get_s3_sections: CreateS3Sections,
    tag_import: TagsOption,
    expected_tags: dict[str, list[str]],
) -> None:
    _s3_limits, s3_summary, _s3, _s3_bucket, _s3_requests = get_s3_sections(tag_import=tag_import)
    s3_summary_results = s3_summary.run().results

    assert s3_summary_results
    for result in s3_summary_results:
        assert result.content
        for row in result.content:
            assert list(row["TagsForCmkLabels"].keys()) == expected_tags.get(row["Name"], [])


def test_agent_aws_s3_puts_each_bucket_on_its_own_host(
    get_s3_sections: CreateS3Sections,
) -> None:
    _s3_limits, s3_summary, s3, s3_bucket, _s3_requests = get_s3_sections()
    s3_summary.run()
    s3.run()

    s3_bucket_results = s3_bucket.run().results

    assert {
        result.piggyback_hostname: {row["Label"] for row in result.content}
        for result in s3_bucket_results
    } == {BUCKET_HOSTS[f"Name-{i}"]: {f"Name-{i}"} for i in range(3)}


def test_agent_aws_s3_bucket_hosts_follow_the_partition_of_the_client(
    get_s3_sections: CreateS3Sections,
) -> None:
    _s3_limits, s3_summary, s3, s3_bucket, _s3_requests = get_s3_sections(partition="aws-cn")
    s3_summary.run()
    s3.run()

    s3_bucket_results = s3_bucket.run().results

    assert {result.piggyback_hostname for result in s3_bucket_results} == {
        "aws_s3_bucket_Name-0_1a0b8c7d",
        "aws_s3_bucket_Name-1_27803d02",
        "aws_s3_bucket_Name-2_eb85b5a2",
    }


def test_agent_aws_s3_bucket_hosts_get_the_resource_labels(
    get_s3_sections: CreateS3Sections,
) -> None:
    _s3_limits, s3_summary, s3, s3_bucket, _s3_requests = get_s3_sections()
    s3_summary.run()
    s3.run()

    results = s3_bucket.run().results

    # Only the first two buckets have tags.
    tags = [
        {"cmk/aws/tag/Key-0": "Value-0"},
        {"cmk/aws/tag/Key-0": "Value-0", "cmk/aws/tag/Key-1": "Value-1"},
        {},
    ]
    assert {result.piggyback_hostname: result.piggyback_host_labels for result in results} == {
        BUCKET_HOSTS[f"Name-{i}"]: {
            "cmk/aws/service": "s3",
            "cmk/aws/name": f"Name-{i}",
            "cmk/aws/resource_id": f"Name-{i}",
            "cmk/aws/region": "region",
            **tags[i],
        }
        for i in range(3)
    }


def test_agent_aws_s3_requests_carry_the_labels_of_their_bucket_host(
    get_s3_sections: CreateS3Sections,
) -> None:
    _s3_limits, s3_summary, s3, s3_bucket, s3_requests = get_s3_sections()
    s3_summary.run()
    s3.run()
    bucket_labels = {
        result.piggyback_hostname: result.piggyback_host_labels
        for result in s3_bucket.run().results
    }

    results = s3_requests.run().results

    assert {
        result.piggyback_hostname: result.piggyback_host_labels for result in results
    } == bucket_labels


def test_agent_aws_s3_creates_no_bucket_host_without_buckets(
    get_s3_sections: CreateS3Sections,
) -> None:
    _s3_limits, s3_summary, s3, s3_bucket, _s3_requests = get_s3_sections(names=["Uuuups"])
    s3_summary.run()
    s3.run()

    s3_bucket_results = s3_bucket.run().results

    assert not s3_bucket_results


class PagedS3Client:
    """Lists one bucket per page, as AWS does for a small MaxBuckets."""

    def list_buckets(self, MaxBuckets: int, ContinuationToken: str = "0") -> Mapping[str, object]:  # noqa: ARG002
        page = int(ContinuationToken)
        buckets = {"Buckets": [{"Name": f"bucket-{page}"}]}
        return buckets if page == 2 else {**buckets, "ContinuationToken": str(page + 1)}

    def get_bucket_location(self, Bucket: str) -> Mapping[str, object]:  # noqa: ARG002
        return {"LocationConstraint": "eu-central-1"}


def test_list_buckets_reads_every_page() -> None:
    buckets = S3BucketHelper.list_buckets(PagedS3Client())

    assert [bucket["Name"] for bucket in buckets] == ["bucket-0", "bucket-1", "bucket-2"]


class AccessDeniedError(Exception):
    pass


class PolicyDeniedS3Client:
    """A bucket whose bucket policy denies GetBucketLocation."""

    exceptions = SimpleNamespace(ClientError=AccessDeniedError)

    def list_buckets(self, MaxBuckets: int) -> Mapping[str, object]:  # noqa: ARG002
        return {"Buckets": [{"Name": "private", "BucketRegion": "eu-central-1"}]}

    def get_bucket_location(self, Bucket: str) -> Mapping[str, object]:
        raise AccessDeniedError(f"Access Denied: {Bucket}")


def test_list_buckets_takes_the_region_from_the_list() -> None:
    [bucket] = S3BucketHelper.list_buckets(PolicyDeniedS3Client())

    assert bucket == {
        "Name": "private",
        "BucketRegion": "eu-central-1",
        "LocationConstraint": "eu-central-1",
    }
