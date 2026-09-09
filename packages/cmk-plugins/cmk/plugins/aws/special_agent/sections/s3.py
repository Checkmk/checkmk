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

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, Literal, override

from botocore.client import BaseClient

from ..config import AWSConfig, LOGGER, Tags
from .core import (
    AWSColleagueContents,
    AWSComputedContent,
    AWSLimit,
    AWSRawContent,
    AWSSection,
    AWSSectionCloudwatch,
    AWSSectionLimits,
    AWSSectionResult,
    get_seconds_since_midnight,
    Metrics,
    NOW,
    ResultDistributor,
)

Buckets = Sequence[Mapping[Literal["Name", "CreationDate"], str | datetime]]


class ResultDistributorS3Limits(ResultDistributor):
    """
    Special mediator for distributing results from S3Limits. This mediator stores any received
    results and distributes both upon receiving and upon adding a new colleague. This is done
    because we want to run S3Limits only once (does not matter for which region, results are the
    same for all regions) and later distribute the results to S3Summary objects in other regions.
    """

    def __init__(self) -> None:
        super().__init__()
        self._received_results: dict[str, tuple[AWSSection, AWSComputedContent]] = {}

    @override
    def add(self, sender_name: str, colleague: AWSSection) -> None:
        super().add(sender_name, colleague)
        for sender, content in self._received_results.values():
            colleague.receive(sender, content)

    @override
    def distribute(self, sender: AWSSection, result: AWSComputedContent) -> None:
        self._received_results.setdefault(sender.name, (sender, result))
        super().distribute(sender, result)

    def is_empty(self) -> bool:
        return len(self._colleagues) == 0


class S3BucketHelper:
    """
    Helper Class for S3
    """

    @staticmethod
    def list_buckets(client: BaseClient) -> Buckets:
        """
        Get all buckets with LocationConstraint
        """
        bucket_list = client.list_buckets()  # type: ignore[attr-defined]
        for bucket in bucket_list["Buckets"]:
            bucket_name = bucket["Name"]

            # request additional LocationConstraint information
            try:
                response = client.get_bucket_location(Bucket=bucket_name)  # type: ignore[attr-defined]
            except client.exceptions.ClientError as e:
                # An error occurred (AccessDenied) when calling the GetBucketLocation operation:
                # Access Denied
                LOGGER.info(
                    "S3BucketHelper/%(bucket_name)s: Access denied, %(error)s",
                    {"bucket_name": bucket_name, "error": e},
                )
                continue

            if response:
                if response["LocationConstraint"] is None:
                    location_constraint = "us-east-1"  # for this region, LocationConstraint is None
                else:
                    location_constraint = response["LocationConstraint"]
                bucket["LocationConstraint"] = location_constraint
        return bucket_list["Buckets"] if bucket_list else []


class S3Limits(AWSSectionLimits):
    @property
    @override
    def name(self) -> str:
        return "s3_limits"

    @property
    @override
    def cache_interval(self) -> int:
        """Return the upper limit for allowed cache age.

        Data is updated at midnight, so the cache should not be older than the day.
        """
        cache_interval = int(get_seconds_since_midnight(NOW))
        LOGGER.debug(
            "Maximal allowed age of usage data cache: %(cache_interval)s sec",
            {"cache_interval": cache_interval},
        )

        return cache_interval

    @property
    @override
    def granularity(self) -> int:
        return 86400

    @override
    def _get_colleague_contents(self) -> AWSColleagueContents:
        return AWSColleagueContents(None, 0.0)

    @override
    def get_live_data(self, *args: AWSColleagueContents) -> Buckets:
        """
        There's no API method for getting account limits thus we have to
        fetch all buckets.
        """
        return S3BucketHelper.list_buckets(self._client)

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        self._add_limit(
            "", AWSLimit("buckets", "Buckets", 100, len(raw_content.content)), region="Global"
        )
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)


class S3Summary(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["s3_names"]
        self._tags = self.prepare_tags_for_api_response(self._config.service_config["s3_tags"])

    @property
    @override
    def name(self) -> str:
        return "s3_summary"

    @property
    @override
    def cache_interval(self) -> int:
        """Return the upper limit for allowed cache age.

        Data is updated at midnight, so the cache should not be older than the day.
        """
        cache_interval = int(get_seconds_since_midnight(NOW))
        LOGGER.debug(
            "Maximal allowed age of usage data cache: %(cache_interval)s sec",
            {"cache_interval": cache_interval},
        )
        return cache_interval

    @property
    @override
    def granularity(self) -> int:
        return 86400

    @override
    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("s3_limits")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    @override
    def get_live_data(self, *args: AWSColleagueContents) -> Sequence[Mapping[str, object]]:
        (colleague_contents,) = args
        found_buckets = []
        for bucket in self._list_buckets(colleague_contents):
            bucket_name = bucket["Name"]

            try:
                response = self._client.get_bucket_tagging(Bucket=bucket_name)  # type: ignore[attr-defined]
            except self._client.exceptions.ClientError as e:
                # If there are no tags attached to a bucket we receive a 'ClientError'
                LOGGER.info(
                    "%(name)s/%(bucket_name)s: No tags set, %(error)s",
                    {"name": self.name, "bucket_name": bucket_name, "error": e},
                )
                response = {}

            tagging = self._get_response_content(response, "TagSet")
            if self._matches_tag_conditions(tagging):
                bucket["Tagging"] = tagging  # Legacy tags, to be removed when check is adapted
                bucket["TagsForCmkLabels"] = self.process_tags_for_cmk_labels(tagging)
                found_buckets.append(bucket)
        return found_buckets

    def _list_buckets(
        self, colleague_contents: AWSColleagueContents
    ) -> Sequence[dict[str, object]]:
        # use previous fetched data or fetch it now
        bucket_list: Any = colleague_contents.content or S3BucketHelper.list_buckets(self._client)

        # filter buckets by region
        bucket_list = [
            bucket
            for bucket in bucket_list
            if "LocationConstraint" in bucket and bucket["LocationConstraint"] == self.region
        ]

        # filter buckets by name if there is a filter
        if self._names is not None:
            return [bucket for bucket in bucket_list if bucket["Name"] in self._names]

        return bucket_list

    def _matches_tag_conditions(self, tagging: Tags) -> bool:
        if self._names is not None:
            return True
        if self._tags is None:
            return True
        return any(tag in self._tags for tag in tagging)

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(
            {bucket["Name"]: bucket for bucket in raw_content.content}, raw_content.cache_timestamp
        )

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", list(computed_content.content.values()))]


class S3(AWSSectionCloudwatch):
    @property
    @override
    def name(self) -> str:
        return "s3"

    @property
    @override
    def cache_interval(self) -> int:
        # BucketSizeBytes and NumberOfObjects are available per day
        # and must include 00:00h
        """Return the upper limit for allowed cache age.

        Data is updated at midnight, so the cache should not be older than the day.
        """
        cache_interval = int(get_seconds_since_midnight(NOW))
        LOGGER.debug(
            "Maximal allowed age of usage data cache: %(cache_interval)s sec",
            {"cache_interval": cache_interval},
        )
        return cache_interval

    @property
    @override
    def granularity(self) -> int:
        return 86400

    @override
    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("s3_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    @override
    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        metrics: Metrics = []
        for idx, bucket_name in enumerate(colleague_contents.content):
            for metric_name, unit, storage_classes in [
                (
                    "BucketSizeBytes",
                    "Bytes",
                    [
                        "StandardStorage",
                        "StandardIAStorage",
                        "ReducedRedundancyStorage",
                    ],
                ),
                ("NumberOfObjects", "Count", ["AllStorageTypes"]),
            ]:
                for storage_class in storage_classes:
                    metrics.append(
                        {
                            "Id": self._create_id_for_metric_data_query(
                                idx, metric_name, storage_class
                            ),
                            "Label": bucket_name,
                            "MetricStat": {
                                "Metric": {
                                    "Namespace": "AWS/S3",
                                    "MetricName": metric_name,
                                    "Dimensions": [
                                        {
                                            "Name": "BucketName",
                                            "Value": bucket_name,
                                        },
                                        {
                                            "Name": "StorageType",
                                            "Value": storage_class,
                                        },
                                    ],
                                },
                                "Period": self.period,
                                "Stat": "Average",
                                "Unit": unit,
                            },
                        }
                    )
        return metrics

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        for row in raw_content.content:
            bucket = colleague_contents.content.get(row["Label"])
            if bucket:
                row.update(bucket)
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]


class S3Requests(AWSSectionCloudwatch):
    @property
    @override
    def name(self) -> str:
        return "s3_requests"

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
        colleague = self._received_results.get("s3_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    @override
    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        metrics: Metrics = []
        for idx, bucket_name in enumerate(colleague_contents.content):
            for metric_name, unit, stat in [
                ("AllRequests", "Count", "Sum"),
                ("GetRequests", "Count", "Sum"),
                ("PutRequests", "Count", "Sum"),
                ("DeleteRequests", "Count", "Sum"),
                ("HeadRequests", "Count", "Sum"),
                ("PostRequests", "Count", "Sum"),
                ("SelectRequests", "Count", "Sum"),
                # The following two metrics seem to have the wrong name in the documentation
                # https://docs.aws.amazon.com/AmazonS3/latest/dev/cloudwatch-monitoring.html
                ("SelectBytesScanned", "Bytes", "Sum"),
                ("SelectBytesReturned", "Bytes", "Sum"),
                ("ListRequests", "Count", "Sum"),
                ("BytesDownloaded", "Bytes", "Sum"),
                ("BytesUploaded", "Bytes", "Sum"),
                ("4xxErrors", "Count", "Sum"),
                ("5xxErrors", "Count", "Sum"),
                ("FirstByteLatency", "Milliseconds", "Average"),
                ("TotalRequestLatency", "Milliseconds", "Average"),
            ]:
                metrics.append(
                    {
                        "Id": self._create_id_for_metric_data_query(idx, metric_name),
                        "Label": bucket_name,
                        "MetricStat": {
                            "Metric": {
                                "Namespace": "AWS/S3",
                                "MetricName": metric_name,
                                "Dimensions": [
                                    {"Name": "BucketName", "Value": bucket_name},
                                    {"Name": "FilterId", "Value": "EntireBucket"},
                                ],
                            },
                            "Period": self.period,
                            "Stat": stat,
                            "Unit": unit,
                        },
                    }
                )
        return metrics

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        for row in raw_content.content:
            bucket = colleague_contents.content.get(row["Label"])
            if bucket:
                row.update(bucket)
        return AWSComputedContent(raw_content.content, raw_content.cache_timestamp)

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]
