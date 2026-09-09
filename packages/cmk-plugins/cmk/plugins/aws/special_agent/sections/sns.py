#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import override

from botocore.client import BaseClient

from ..config import AWSConfig
from .core import (
    AWSColleagueContents,
    AWSComputedContent,
    AWSLimit,
    AWSRawContent,
    AWSSection,
    AWSSectionCloudwatch,
    AWSSectionLimits,
    AWSSectionResult,
    fetch_resource_tags_from_types,
    filter_resources_matching_tags,
    Metric,
    Metrics,
    ResourceTags,
    ResultDistributor,
)


@dataclass(frozen=True)
class SNSTopic:
    region: str
    account_id: str
    topic_name: str

    @classmethod
    def from_arn(cls: type[SNSTopic], arn_str: str) -> SNSTopic:
        """Example topic ARN: 'arn:aws:sns:eu-central-1:710145618630:TestTopicGiordano'"""
        splitted_arn = arn_str.split(":")
        return cls(region=splitted_arn[3], account_id=splitted_arn[4], topic_name=splitted_arn[5])

    def to_arn(self) -> str:
        return f"arn:aws:sns:{self.region}:{self.account_id}:{self.topic_name}"

    def to_item_id(self) -> str:
        """Return the item id of the CheckMK service."""
        # !!!DO NOT CHANGE THE ITEM ID!!!!
        # If you change the item id, it will create new services and lose all the data of the old
        # services because the service name will change according to the item id

        # SNS Topic name is unique per region so we need to include the region name in the service
        # name to avoid considering 2 topics with the same name in different regions as the same
        # topic
        return f"{self.topic_name} [{self.region}]"


class SNSTopicsFetcher:
    """This class will fetch the topics matching the config criteria and cache them in memory"""

    def __init__(
        self,
        client: BaseClient,
        tagging_client: BaseClient,
        region: str,
        config: AWSConfig,
    ):
        self._client = client
        self._tagging_client = tagging_client
        self._region = region
        self._names = config.service_config["sns_names"]
        self._tags = AWSSection.prepare_tags_for_api_response(config.service_config["sns_tags"])

    def fetch_all_topics(self) -> list[SNSTopic]:
        return [
            SNSTopic.from_arn(topic["TopicArn"])
            for page in self._client.get_paginator("list_topics").paginate()
            for topic in page["Topics"]
        ]

    def fetch_all_topic_tags(self) -> ResourceTags:
        return fetch_resource_tags_from_types(self._tagging_client, ["sns:topic"])

    def filter_topics(self, all_topics_arns: list[str], resource_tags: ResourceTags) -> list[str]:
        if self._tags:
            topics_arn_matching_tags = filter_resources_matching_tags(resource_tags, self._tags)
            return [t for t in all_topics_arns if t in topics_arn_matching_tags]

        if self._names:
            return [t for t in all_topics_arns if SNSTopic.from_arn(t).topic_name in self._names]

        return all_topics_arns


class SNSLimits(AWSSectionLimits):
    """
    AWS imposes the following per account limits.
    Topics (Standard): 100k
    Topics (FIFO): 1k
    Subscriptions (Standard): 12.5M
    Subscriptions (FIFO): 100
    There are many other limits related to how many API requests one can make per second for
    various tasks, but these four limits above are the most account-relevant limits.
    This article might also be a valuable resource: https://www.serverless.com/guides/amazon-sns#:~:text=Amazon%20SNS%20limits,-%E2%80%8D&text=Both%20subscribe%20and%20unsubscribe%20transactions,the%20us%2Deast%2D1%20region
    """

    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        sns_topics_fetcher: SNSTopicsFetcher,
        distributor: ResultDistributor | None = None,
    ):
        super().__init__(client, region, config, distributor=distributor)
        self._sns_topics_fetcher = sns_topics_fetcher

    @property
    @override
    def name(self) -> str:
        return "sns_limits"

    @property
    @override
    def cache_interval(self) -> int:
        return 300

    @property
    @override
    def granularity(self) -> int:
        return 300

    @override
    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents(None, 0.0)

    @override
    def get_live_data(self, *args: AWSColleagueContents) -> Sequence[Mapping]:
        # We don't want to filter by name and tags for the limits section since the filtered topics
        # are considered in the AWS account limits
        topics = self._sns_topics_fetcher.fetch_all_topics()

        num_of_subscriptions_by_topic = Counter(
            str(subscription["TopicArn"])
            for page in self._client.get_paginator("list_subscriptions").paginate()
            for subscription in page["Subscriptions"]
        )

        return [
            {
                "arn": topic.to_arn(),
                "is_fifo": topic.topic_name.endswith(".fifo"),
                "num_subscriptions": num_of_subscriptions_by_topic[topic.to_arn()],
            }
            for topic in topics
        ]

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        topics: Sequence[Mapping] = raw_content.content

        self._add_limit(
            "",
            AWSLimit(
                key="topics_standard",
                title="Standard Topics",
                limit=int(100e3),
                amount=sum(not x["is_fifo"] for x in topics),
            ),
            region=self._region,
        )
        self._add_limit(
            "",
            AWSLimit(
                key="topics_fifo",
                title="FIFO Topics",
                limit=int(1e3),
                amount=sum(x["is_fifo"] for x in topics),
            ),
            region=self._region,
        )

        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)


class SNSSummary(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        sns_topics_fetcher: SNSTopicsFetcher,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._sns_topics_fetcher = sns_topics_fetcher

    @property
    @override
    def name(self) -> str:
        return "sns_summary"

    @property
    @override
    def cache_interval(self) -> int:
        return 300

    @property
    @override
    def granularity(self) -> int:
        return 300

    @override
    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("sns_limits")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    @override
    def get_live_data(self, *args: AWSColleagueContents) -> Sequence[object]:
        (colleague_contents,) = args

        if colleague_contents.content:
            topics_arn = [topic["arn"] for topic in colleague_contents.content]
        else:
            topics_arn = [topic.to_arn() for topic in self._sns_topics_fetcher.fetch_all_topics()]

        tags = self._sns_topics_fetcher.fetch_all_topic_tags()
        filtered_topics = self._sns_topics_fetcher.filter_topics(topics_arn, tags)

        found_topics = []
        for topic_arn in topics_arn:
            if topic_arn in filtered_topics:
                topic = SNSTopic.from_arn(topic_arn)
                found_topics.append(
                    {
                        "Name": topic.topic_name,
                        "ARN": topic_arn,
                        "ItemId": topic.to_item_id(),
                        "Region": topic.region,
                        "AccountId": topic.account_id,
                        "TagsForCmkLabels": self.process_tags_for_cmk_labels(
                            tags.get(topic_arn, [])
                        ),
                    }
                )

        return found_topics

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]


class SNSSMS(AWSSectionCloudwatch):
    @property
    @override
    def name(self) -> str:
        return "sns_sms_cloudwatch"

    @property
    @override
    def cache_interval(self) -> int:
        return 300

    @property
    @override
    def granularity(self) -> int:
        return 300

    @override
    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents({}, 0.0)

    @override
    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        # The metrics of this class are grouped by AWS region because AWS doesn't provide SMS-relatd
        # metrics on a per-topic level but only per-region
        sms_success_rate_metric: Metric = {
            "Id": self._create_id_for_metric_data_query(0, "SMSSuccessRate"),
            "Label": self.region,
            "Period": self.period,
            "Expression": 'SELECT AVG(SMSSuccessRate) FROM SCHEMA("AWS/SNS", Country,SMSType)',
        }
        sms_spending_metric: Metric = {
            "Id": self._create_id_for_metric_data_query(0, "SMSMonthToDateSpentUSD"),
            "Label": self.region,
            "MetricStat": {
                "Metric": {
                    "Namespace": "AWS/SNS",
                    "MetricName": "SMSMonthToDateSpentUSD",
                    "Dimensions": [],
                },
                "Period": self.period,
                "Stat": "Maximum",
                "Unit": "Count",
            },
        }
        return [sms_success_rate_metric, sms_spending_metric]

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]


class SNS(AWSSectionCloudwatch):
    def __init__(self, client: BaseClient, region: str, config: AWSConfig):
        super().__init__(client, region, config)

    @property
    @override
    def name(self) -> str:
        return "sns_cloudwatch"

    @property
    @override
    def cache_interval(self) -> int:
        return 300

    @property
    @override
    def granularity(self) -> int:
        return 300

    @override
    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("sns_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    @override
    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        # The metrics of this class are grouped by SNS topic
        metrics = []
        for idx, topic in enumerate(colleague_contents.content):
            for metric_name, stat, unit in [
                ("NumberOfMessagesPublished", "Sum", "Count"),
                ("NumberOfNotificationsDelivered", "Sum", "Count"),
                ("NumberOfNotificationsFailed", "Sum", "Count"),
            ]:
                metric: Metric = {
                    "Id": self._create_id_for_metric_data_query(idx, metric_name),
                    "Label": topic["ItemId"],
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/SNS",
                            "MetricName": metric_name,
                            "Dimensions": [
                                {
                                    "Name": "TopicName",
                                    "Value": topic["Name"],
                                }
                            ],
                        },
                        "Period": self.period,
                        "Stat": stat,
                        "Unit": unit,
                    },
                }
                metrics.append(metric)
        return metrics

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]
