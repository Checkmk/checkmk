#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

from collections.abc import Callable, Iterable, Mapping, Sequence
from unittest.mock import MagicMock

import pytest

from cmk.special_agents.agent_aws import (
    AWSConfig,
    AWSRegionLimit,
    NamingConvention,
    OverallTags,
    SNS,
    SNSLimits,
    SNSSMS,
    SNSTopicsFetcher,
)

from .agent_aws_fake_clients import FakeCloudwatchClient, SNSListSubscriptionsIB, SNSListTopicsIB

SNSSectionsGetter = Callable[[list[str] | None, OverallTags], tuple[SNSSMS, SNS]]

ALL_TOPICS = {
    "eu-west-1 TopicName-0",
    "eu-west-1 TopicName-1",
    "eu-west-1 TopicName-2",
    "eu-west-1 TopicName-3.fifo",
    "eu-west-1 TopicName-4.fifo",
}

TAGGING_PAGINATOR_RESULT = {
    "PaginationToken": "",
    "ResourceTagMappingList": [
        {
            "ResourceARN": "arn:aws:sns:eu-west-1:710145618630:TopicName-3.fifo",
            "Tags": [{"Key": "test-tag-key", "Value": "test-tag-value"}],
        }
    ],
    "ResponseMetadata": {
        "RequestId": "f8ddd3c3-9657-4de5-a3e4-d997eddabec3",
        "HTTPStatusCode": 200,
        "HTTPHeaders": {
            "x-amzn-requestid": "f8ddd3c3-9657-4de5-a3e4-d997eddabec3",
            "content-type": "application/x-amz-json-1.1",
            "content-length": "164",
            "date": "Tue, 27 Dec 2022 16:50:02 GMT",
        },
        "RetryAttempts": 0,
    },
}


class PaginatorTopics:
    def __init__(self, topics: Sequence[Mapping]) -> None:
        self._topics = topics

    def paginate(self) -> Iterable[Mapping]:
        yield {
            "Topics": self._topics,
        }


class PaginatorSubscriptions:
    def __init__(self, subscriptions: Sequence[Mapping]) -> None:
        self._subscriptions = subscriptions

    def paginate(self) -> Iterable[Mapping]:
        yield {
            "Subscriptions": self._subscriptions,
        }


class TaggingPaginator:
    def paginate(self, *args, **kwargs):
        yield TAGGING_PAGINATOR_RESULT


class FakeTaggingClient:
    def get_paginator(self, operation_name):
        if operation_name == "get_resources":
            return TaggingPaginator()
        raise NotImplementedError


class FakeSNSClient:
    def __init__(self, n_std_topics: int, n_fifo_topics: int, n_subs: int) -> None:
        self._topics = SNSListTopicsIB.create_instances(amount=n_std_topics + n_fifo_topics)
        for idx in range(n_fifo_topics):
            self._topics[-(idx + 1)]["TopicArn"] += ".fifo"
        self._subscriptions = SNSListSubscriptionsIB.create_instances(amount=n_subs)

    def get_paginator(self, operation_name):
        if operation_name == "list_topics":
            return PaginatorTopics(self._topics)
        if operation_name == "list_subscriptions":
            return PaginatorSubscriptions(self._subscriptions)
        raise NotImplementedError


def _create_sns_limits(n_std_topics: int, n_fifo_topics: int, n_subs: int) -> SNSLimits:
    config = AWSConfig("hostname", [], ([], []), NamingConvention.ip_region_instance)
    config.add_single_service_config("sns_names", [])
    config.add_single_service_config("sns_tags", [])
    fake_sns_client = FakeSNSClient(n_std_topics, n_fifo_topics, n_subs)
    # TODO: FakeSNSClient shoud actually subclass SNSClient.
    topics_fetcher = SNSTopicsFetcher(fake_sns_client, MagicMock(), "region", config)  # type: ignore[arg-type]
    return SNSLimits(
        client=fake_sns_client,  # type: ignore[arg-type]
        region="region",
        config=config,
        sns_topics_fetcher=topics_fetcher,
    )


@pytest.mark.parametrize(
    ["n_std_topics", "n_fifo_topics", "n_subs"],
    [pytest.param(0, 0, 0, id="no sns services"), pytest.param(3, 3, 3, id="some sns data")],
)
def test_agent_aws_sns_limits(n_std_topics: int, n_fifo_topics: int, n_subs: int) -> None:
    sns_limits = _create_sns_limits(n_std_topics, n_fifo_topics, n_subs)
    sns_limits_results = sns_limits.run().results

    assert sns_limits.cache_interval == 300
    assert sns_limits.period == 600
    assert sns_limits.name == "sns_limits"
    limits_topics_standard: AWSRegionLimit = sns_limits_results[0].content[0]
    limits_topics_fifo: AWSRegionLimit = sns_limits_results[0].content[1]
    assert limits_topics_standard.amount == n_std_topics
    assert limits_topics_fifo.amount == n_fifo_topics


@pytest.fixture()
def get_sns_sections() -> SNSSectionsGetter:
    def _create_sns_sections(names: list[str] | None, tags: OverallTags) -> tuple[SNSSMS, SNS]:
        region = "eu-west-1"
        config = AWSConfig("hostname", [], ([], []), NamingConvention.ip_region_instance)
        config.add_single_service_config("sns_names", names)
        config.add_service_tags("sns_tags", tags)

        fake_sns_client = FakeSNSClient(n_std_topics=3, n_fifo_topics=2, n_subs=7)
        fake_cloudwatch_client = FakeCloudwatchClient()
        fake_tagging_client = FakeTaggingClient()

        # TODO: FakeSNSClient shoud actually subclass SNSClient, FakeCloudwatchClient should subclass CloudWatchClient, etc.
        sns_topics_fetcher = SNSTopicsFetcher(fake_sns_client, fake_tagging_client, region, config)  # type: ignore[arg-type]
        sns_sms = SNSSMS(fake_cloudwatch_client, region, config)  # type: ignore[arg-type]
        sns = SNS(fake_cloudwatch_client, region, config, sns_topics_fetcher)  # type: ignore[arg-type]
        return sns_sms, sns

    return _create_sns_sections


sns_params = [
    (None, (None, None), ALL_TOPICS),
    (
        ["TopicName-1", "TopicName-4.fifo"],
        (None, None),
        ["eu-west-1 TopicName-1", "eu-west-1 TopicName-4.fifo"],
    ),
    (None, ([["test-tag-key"]], [["test-tag-value"]]), ["eu-west-1 TopicName-3.fifo"]),
    (None, ([["test-tag-key"]], [["wrong-tag-value"]]), []),
    (None, ([["wrong-tag-key"]], [["test-tag-value"]]), []),
    (["NONEXISTINGID"], (None, None), []),
]


@pytest.mark.parametrize("names, tags, found_services_name", sns_params)
def test_agent_aws_sns(
    get_sns_sections: SNSSectionsGetter,
    names: list[str] | None,
    tags: OverallTags,
    found_services_name: list[str],
) -> None:
    _sns_sms, sns = get_sns_sections(names, tags)
    assert sns.name == "sns_cloudwatch"
    perform_agent_aws_sns_test(sns, found_services_name, 3)


# Cloudwatch doesn't provide SNS SMS data by SNS Topic so names and tags are ignored since they
# can't be applied
sns_sms_params = [
    (None, (None, None), ["eu-west-1"]),
    (
        ["TopicName-1", "TopicName-4.fifo"],
        (None, None),
        ["eu-west-1"],
    ),
    (None, ([["test-tag-key"]], [["test-tag-value"]]), ["eu-west-1"]),
    (None, ([["test-tag-key"]], [["wrong-tag-value"]]), ["eu-west-1"]),
    (None, ([["wrong-tag-key"]], [["test-tag-value"]]), ["eu-west-1"]),
    (["NONEXISTINGID"], (None, None), ["eu-west-1"]),
]


@pytest.mark.parametrize("names, tags, found_services_name", sns_sms_params)
def test_agent_aws_sns_sms(
    get_sns_sections: SNSSectionsGetter,
    names: list[str] | None,
    tags: OverallTags,
    found_services_name: list[str],
) -> None:
    sns_sms, _sns = get_sns_sections(names, tags)
    assert sns_sms.name == "sns_sms_cloudwatch"
    perform_agent_aws_sns_test(sns_sms, found_services_name, 2)


def perform_agent_aws_sns_test(
    sns_section: SNSSMS | SNS, found_services_name: list[str], metrics_per_topic: int
) -> None:
    assert sns_section.cache_interval == 300
    assert sns_section.period == 600

    sns_results = sns_section.run().results

    if found_services_name:
        assert len(sns_results) == 1
        sns_result = sns_results[0]
        assert sns_result.piggyback_hostname == ""
        assert {e["Label"] for e in sns_result.content} == set(found_services_name)
        assert len(sns_result.content) == metrics_per_topic * len(found_services_name)
    else:
        assert len(sns_results) == 0
