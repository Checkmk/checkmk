#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

from datetime import datetime as dt

import pytest

# Needed to monkeypatch agent_aws.NOW
from cmk.special_agents import agent_aws
from cmk.special_agents.agent_aws import (
    AWSConfig,
    ResultDistributor,
    S3,
    S3Limits,
    S3Requests,
    S3Summary,
)

from .agent_aws_fake_clients import FakeCloudwatchClient, S3BucketTaggingIB, S3ListBucketsIB


class FakeS3Client:
    def list_buckets(self):
        return {
            "Buckets": S3ListBucketsIB.create_instances(amount=4),
            "Owner": {
                "DisplayName": "string",
                "ID": "string",
            },
        }

    def get_bucket_location(self, Bucket=""):
        if Bucket in ["Name-0", "Name-1", "Name-2"]:
            return {
                "LocationConstraint": "region",
            }
        return {}

    def get_bucket_tagging(self, Bucket=""):
        if Bucket == "Name-0":
            return {
                "TagSet": S3BucketTaggingIB.create_instances(amount=1),
            }
        if Bucket == "Name-1":
            return {
                "TagSet": S3BucketTaggingIB.create_instances(amount=2),
            }
        return {}


@pytest.fixture()
def get_s3_sections(monkeypatch):
    def _create_s3_sections(names, tags):
        # on_time is somehow not feeded from here to S3Limits, so use monkey patch...
        monkeypatch.setattr(
            agent_aws, "NOW", dt.strptime("2020-09-28 15:30 UTC", "%Y-%m-%d %H:%M %Z")
        )

        region = "region"
        config = AWSConfig("hostname", [], (None, None))
        config.add_single_service_config("s3_names", names)
        config.add_service_tags("s3_tags", tags)

        fake_s3_client = FakeS3Client()
        fake_cloudwatch_client = FakeCloudwatchClient()

        s3_limits_distributor = ResultDistributor()
        s3_summary_distributor = ResultDistributor()

        s3_limits = S3Limits(fake_s3_client, region, config, s3_limits_distributor)
        s3_summary = S3Summary(fake_s3_client, region, config, s3_summary_distributor)
        s3 = S3(fake_cloudwatch_client, region, config)
        s3_requests = S3Requests(fake_cloudwatch_client, region, config)

        s3_limits_distributor.add(s3_summary)
        s3_summary_distributor.add(s3)
        s3_summary_distributor.add(s3_requests)
        return s3_limits, s3_summary, s3, s3_requests

    return _create_s3_sections


s3_params = [
    (None, (None, None), 3),
    (["Name-0"], (None, None), 1),
    (["Name-0", "Name-1"], (None, None), 2),
    (["Name-0", "Name-1", "Name-2"], (None, None), 3),
    (["Name-0", "Name-1", "Name-2", "string4"], (None, None), 3),
    (["Name-0", "Name-1", "Name-2", "FOOBAR"], (None, None), 3),
    (["Name-0"], ([["Key-0", "unknown-tag"]], [["Value-0", "Value-1"], ["unknown-val"]]), 1),
    (
        ["Name-0", "Name-1"],
        ([["Key-0", "unknown-tag"]], [["Value-0", "Value-1"], ["unknown-val"]]),
        2,
    ),
    (
        ["Name-0", "Name-1", "Name-2"],
        ([["Key-0", "unknown-tag"]], [["Value-0", "Value-1"], ["unknown-val"]]),
        3,
    ),
    (
        ["Name-0", "Name-1", "Name-2", "string4"],
        ([["Key-0", "unknown-tag"]], [["Value-0", "Value-1"], ["unknown-val"]]),
        3,
    ),
    (
        ["Name-0", "Name-1", "Name-2", "FOOBAR"],
        ([["Key-0", "unknown-tag"]], [["Value-0", "Value-1"], ["unknown-val"]]),
        3,
    ),
    (
        None,
        (
            [
                ["Key-1"],
            ],
            [
                [
                    "Value-0",
                ],
            ],
        ),
        0,
    ),
    (
        None,
        (
            [
                ["Key-1"],
            ],
            [
                [
                    "Value-1",
                ],
            ],
        ),
        1,
    ),
    (
        None,
        (
            [
                ["Key-0"],
            ],
            [
                [
                    "Value-0",
                ],
            ],
        ),
        2,
    ),
    (
        None,
        (
            [
                ["Key-0"],
            ],
            [
                [
                    "Value-0",
                    "Value-1",
                ],
            ],
        ),
        2,
    ),
    (
        None,
        (
            [
                ["Key-0", "unknown-tag"],
            ],
            [
                [
                    "Value-0",
                    "Value-1",
                ],
                [
                    "unknown-val",
                ],
            ],
        ),
        2,
    ),
]


@pytest.mark.parametrize("names,tags,amount_buckets", s3_params)
def test_agent_aws_s3_limits(get_s3_sections, names, tags, amount_buckets):
    s3_limits, _s3_summary, _s3, _s3_requests = get_s3_sections(names, tags)
    s3_limits_results = s3_limits.run().results

    assert s3_limits.name == "s3_limits"

    assert len(s3_limits_results) == 1

    s3_limits_result = s3_limits_results[0]
    assert s3_limits_result.piggyback_hostname == ""
    assert len(s3_limits_result.content) == 1

    s3_limits_content = s3_limits_result.content[0]
    assert s3_limits_content.key == "buckets"
    assert s3_limits_content.title == "Buckets"
    assert s3_limits_content.limit == 100
    assert s3_limits_content.amount == 4


@pytest.mark.parametrize("names,tags,amount_buckets", s3_params)
def test_agent_aws_s3_summary(get_s3_sections, names, tags, amount_buckets):
    s3_limits, s3_summary, _s3, _s3_requests = get_s3_sections(names, tags)
    _s3_summary_results = s3_limits.run().results
    s3_summary_results = s3_summary.run().results

    assert s3_summary.name == "s3_summary"

    assert s3_summary_results == []


@pytest.mark.parametrize("names,tags,amount_buckets", s3_params)
def test_agent_aws_s3(get_s3_sections, names, tags, amount_buckets):
    s3_limits, s3_summary, s3, _s3_requests = get_s3_sections(names, tags)
    _s3_limits_results = s3_limits.run().results
    _s3_summary_results = s3_summary.run().results
    s3_results = s3.run().results
    assert s3.name == "s3"

    if amount_buckets:

        assert len(s3_results) == 1
        s3_result = s3_results[0]
        assert s3_result.piggyback_hostname == ""

        # Y (len results) == 4 (metrics) * X (buckets)
        assert len(s3_result.content) == 4 * amount_buckets
        for row in s3_result.content:
            if row.get("Name") in ["Name-0", "Name-1", "Name-2"]:
                assert row.get("LocationConstraint") == "region"
            assert "Tagging" in row


@pytest.mark.parametrize("names,tags,amount_buckets", s3_params)
def test_agent_aws_s3_requests(get_s3_sections, names, tags, amount_buckets):
    s3_limits, s3_summary, _s3, s3_requests = get_s3_sections(names, tags)
    _s3_limits_results = s3_limits.run().results
    _s3_summary_results = s3_summary.run().results
    s3_requests_results = s3_requests.run().results

    assert s3_requests.cache_interval == 300
    assert s3_requests.period == 600
    assert s3_requests.name == "s3_requests"

    if amount_buckets:
        assert len(s3_requests_results) == 1

        s3_requests_result = s3_requests_results[0]
        assert s3_requests_result.piggyback_hostname == ""

        # Y (len results) == 16 (metrics) * X (buckets)
        assert len(s3_requests_result.content) == 16 * amount_buckets
        for row in s3_requests_result.content:
            if row.get("Name") in ["Name-0", "Name-1", "Name-2"]:
                assert row.get("LocationConstraint") == "region"
            assert "Tagging" in row


@pytest.mark.parametrize("names,tags,amount_buckets", s3_params)
def test_agent_aws_s3_summary_without_limits(get_s3_sections, names, tags, amount_buckets):
    _s3_limits, s3_summary, _s3, _s3_requests = get_s3_sections(names, tags)
    s3_summary_results = s3_summary.run().results

    assert s3_summary.name == "s3_summary"
    assert s3_summary_results == []


@pytest.mark.parametrize("names,tags,amount_buckets", s3_params)
def test_agent_aws_s3_without_limits(get_s3_sections, names, tags, amount_buckets):
    _s3_limits, s3_summary, s3, _s3_requests = get_s3_sections(names, tags)
    _s3_summary_results = s3_summary.run().results
    s3_results = s3.run().results

    assert s3.name == "s3"

    if amount_buckets:
        assert len(s3_results) == 1
        s3_result = s3_results[0]
        assert s3_result.piggyback_hostname == ""

        # Y (len results) == 4 (metrics) * X (buckets)
        assert len(s3_result.content) == 4 * amount_buckets
        for row in s3_result.content:
            if row.get("Name") in ["Name-0", "Name-1", "Name-2"]:
                assert row.get("LocationConstraint") == "region"
            assert "Tagging" in row


@pytest.mark.parametrize("names,tags,amount_buckets", s3_params)
def test_agent_aws_s3_requests_without_limits(get_s3_sections, names, tags, amount_buckets):
    s3_limits, s3_summary, _s3, s3_requests = get_s3_sections(names, tags)
    _s3_summary_results = s3_summary.run().results
    s3_requests_results = s3_requests.run().results

    assert s3_requests.cache_interval == 300
    assert s3_requests.period == 600
    assert s3_requests.name == "s3_requests"

    assert s3_limits.cache_interval == 55800
    assert s3_limits.period == 172800

    if amount_buckets:
        assert len(s3_requests_results) == 1

        s3_requests_result = s3_requests_results[0]
        assert s3_requests_result.piggyback_hostname == ""

        # Y (len results) == 16 (metrics) * X (buckets)
        assert len(s3_requests_result.content) == 16 * amount_buckets
        for row in s3_requests_result.content:
            if row.get("Name") in ["Name-0", "Name-1", "Name-2"]:
                assert row.get("LocationConstraint") == "region"
            assert "Tagging" in row
