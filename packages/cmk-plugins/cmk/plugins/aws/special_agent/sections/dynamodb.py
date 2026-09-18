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

from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import override

from botocore.client import BaseClient

from ..config import AWSConfig, Tags
from .core import (
    AWSColleagueContents,
    AWSComputedContent,
    AWSLimit,
    AWSRawContent,
    AWSSection,
    AWSSectionCloudwatch,
    AWSSectionLabels,
    AWSSectionLimits,
    AWSSectionResult,
    Dimension,
    hostname_from_name_and_region,
    Metrics,
    ResultDistributor,
)


def _get_table_names(client: BaseClient, get_response_content: Callable) -> Iterable[str]:
    for page in client.get_paginator("list_tables").paginate():
        yield from get_response_content(page, "TableNames")


def _describe_dynamodb_tables(
    client: BaseClient,
    get_response_content: Callable,
    fetched_table_names: Sequence[str] | None = None,
) -> Sequence[dict[str, object]]:
    table_names = (
        fetched_table_names
        if fetched_table_names is not None
        else _get_table_names(client, get_response_content)
    )

    tables = []
    for table_name in table_names:
        try:
            tables.append(
                get_response_content(client.describe_table(TableName=table_name), "Table")  # type: ignore[attr-defined]
            )
        # NOTE: The suppression below is needed because of BaseClientExceptions.__getattr__ magic.
        except client.exceptions.ResourceNotFoundException:  # type: ignore[misc]
            # we raise the exception if we fetched the table names from the API, since in that case
            # all tables should exist, otherwise something went really wrong
            if fetched_table_names is None:
                raise

    return tables


class DynamoDB(AWSSection):
    @property
    @override
    def name(self) -> str:
        return "dynamodb"

    @property
    @override
    def cache_interval(self) -> int:
        return 300

    @property
    @override
    def granularity(self) -> int:
        return 300

    @property
    def host_labels(self) -> Mapping[str, str]:
        return {"cmk/aws/service": "dynamodb"}

    @override
    def get_live_data(self, *args: AWSColleagueContents) -> Sequence[Mapping[str, str]] | None:
        (colleague_contents,) = args
        return colleague_contents.content

    @override
    def _get_colleague_contents(self) -> AWSColleagueContents:
        colleague = self._received_results.get("dynamodb_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        content_by_piggyback_hosts: dict[str, list[str]] = {}
        for row in colleague_contents.content:
            content_by_piggyback_hosts.setdefault(row, []).append(row)

        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [
            AWSSectionResult(piggyback_hostname, rows, self.host_labels)
            for piggyback_hostname, rows in computed_content.content.items()
        ]


class DynamoDBLabelsGeneric(AWSSectionLabels):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
        resource: str = "",
    ) -> None:
        self._resource = resource
        super().__init__(client, region, config, distributor=distributor)

    @property
    @override
    def name(self) -> str:
        return "%s_generic_labels" % self._resource

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
        colleague = self._received_results.get("%s_summary" % self._resource)
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    @override
    def get_live_data(self, *args: AWSColleagueContents) -> object:
        (colleague_contents,) = args
        return colleague_contents.content

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        computed_content = {
            elb_instance_id: data.get("TagsForCmkLabels")
            for elb_instance_id, data in raw_content.content.items()
            if data.get("TagsForCmkLabels")
        }
        return AWSComputedContent(computed_content, raw_content.cache_timestamp)


class DynamoDBLimits(AWSSectionLimits):
    @property
    @override
    def name(self) -> str:
        return "dynamodb_limits"

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
    def get_live_data(self, *args):
        """
        The AWS/DynamoDB API method 'describe_limits' provides limits only, but no usage data. We
        therefore gather a list of tables using the method 'list_tables' and check the usage of each
        table via 'describe_table'. See also
        https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_DescribeLimits.html.
        """
        limits = self._client.describe_limits()  # type: ignore[attr-defined]
        tables = _describe_dynamodb_tables(self._client, self._get_response_content)
        return tables, limits

    def _add_read_write_limits(
        self,
        piggyback_hostname: str,
        read_usage: int,
        write_usage: int,
        read_limit: int,
        write_limit: int,
    ) -> None:
        self._add_limit(
            piggyback_hostname,
            AWSLimit(
                "read_capacity",
                "Read Capacity",
                read_limit,
                read_usage,
            ),
        )

        self._add_limit(
            piggyback_hostname,
            AWSLimit(
                "write_capacity",
                "Write Capacity",
                write_limit,
                write_usage,
            ),
        )

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        tables, limits = raw_content.content
        account_read_usage = 0
        account_write_usage = 0

        for table in tables:
            key_usage = "ProvisionedThroughput"
            table_usage_read = table[key_usage]["ReadCapacityUnits"]
            table_usage_write = table[key_usage]["WriteCapacityUnits"]

            # in this case we have an on-demand table, which has no set values for read/write;
            # provisioned tables have a minimum of 1 here
            if table_usage_read == table_usage_write == 0:
                continue

            for global_sec_index in table.get("GlobalSecondaryIndexes", []):
                table_usage_read += global_sec_index[key_usage]["ReadCapacityUnits"]
                table_usage_write += global_sec_index[key_usage]["WriteCapacityUnits"]

            account_read_usage += table_usage_read
            account_write_usage += table_usage_write

            self._add_read_write_limits(
                hostname_from_name_and_region(table["TableName"], self._region),
                table_usage_read,
                table_usage_write,
                limits["TableMaxReadCapacityUnits"],
                limits["TableMaxWriteCapacityUnits"],
            )

        self._add_limit(
            "",
            AWSLimit(
                "number_of_tables",
                "Number of tables",
                256,  # describe_limits does not provide limits for this
                len(tables),
            ),
        )
        self._add_read_write_limits(
            "",
            account_read_usage,
            account_write_usage,
            limits["AccountMaxReadCapacityUnits"],
            limits["AccountMaxWriteCapacityUnits"],
        )

        return AWSComputedContent(tables, raw_content.cache_timestamp)


class DynamoDBSummary(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["dynamodb_names"]
        self._tags = self.prepare_tags_for_api_response(
            self._config.service_config["dynamodb_tags"]
        )

    @property
    @override
    def name(self) -> str:
        return "dynamodb_summary"

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
        colleague = self._received_results.get("dynamodb_limits")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents([], 0.0)

    @override
    def get_live_data(self, *args: AWSColleagueContents) -> Sequence[object]:
        (colleague_contents,) = args

        found_tables = []

        for table in self._describe_tables(colleague_contents):
            assert isinstance(table["TableArn"], str)
            tags = self._get_table_tags(table["TableArn"])

            if self._matches_tag_conditions(tags):
                table["Region"] = self._region
                table["TagsForCmkLabels"] = self.process_tags_for_cmk_labels(tags)
                found_tables.append(table)

        return found_tables

    def _get_table_tags(self, table_arn: str) -> Tags:
        tags = []
        paginator = self._client.get_paginator("list_tags_of_resource")
        response_iterator = paginator.paginate(ResourceArn=table_arn)
        for page in response_iterator:
            tags.extend(self._get_response_content(page, "Tags"))
        return tags

    def _describe_tables(
        self, colleague_contents: AWSColleagueContents
    ) -> Sequence[dict[str, object]]:
        if self._names is None:
            if colleague_contents.content:
                return colleague_contents.content
            return _describe_dynamodb_tables(self._client, self._get_response_content)

        if colleague_contents.content:
            return [
                table for table in colleague_contents.content if table["TableName"] in self._names
            ]
        return _describe_dynamodb_tables(
            self._client, self._get_response_content, fetched_table_names=self._names
        )

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
        content_by_piggyback_hosts: dict[str, str] = {}
        for table in raw_content.content:
            content_by_piggyback_hosts.setdefault(
                hostname_from_name_and_region(table["TableName"], self._region), table
            )
        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", list(computed_content.content.values()))]


class DynamoDBTable(AWSSectionCloudwatch):
    @property
    @override
    def name(self) -> str:
        return "dynamodb_table"

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
        colleague = self._received_results.get("dynamodb_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    @override
    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        metrics: Metrics = []

        for idx, (piggyback_hostname, table) in enumerate(colleague_contents.content.items()):
            for metric_name, stat, operation_dim, unit in [
                ("ConsumedReadCapacityUnits", "Minimum", "", "Count"),
                ("ConsumedReadCapacityUnits", "Maximum", "", "Count"),
                ("ConsumedReadCapacityUnits", "Sum", "", "Count"),
                ("ConsumedWriteCapacityUnits", "Minimum", "", "Count"),
                ("ConsumedWriteCapacityUnits", "Maximum", "", "Count"),
                ("ConsumedWriteCapacityUnits", "Sum", "", "Count"),
                ("SuccessfulRequestLatency", "Maximum", "Query", "Milliseconds"),
                ("SuccessfulRequestLatency", "Average", "Query", "Milliseconds"),
                ("SuccessfulRequestLatency", "Maximum", "GetItem", "Milliseconds"),
                ("SuccessfulRequestLatency", "Average", "GetItem", "Milliseconds"),
                ("SuccessfulRequestLatency", "Maximum", "PutItem", "Milliseconds"),
                ("SuccessfulRequestLatency", "Average", "PutItem", "Milliseconds"),
            ]:
                dimensions: list[Dimension] = [{"Name": "TableName", "Value": table["TableName"]}]

                if operation_dim:
                    dimensions.append({"Name": "Operation", "Value": operation_dim})
                    ident = self._create_id_for_metric_data_query(
                        idx, metric_name, operation_dim, stat
                    )
                else:
                    ident = self._create_id_for_metric_data_query(idx, metric_name, stat)

                metrics.append(
                    {
                        "Id": ident,
                        "Label": piggyback_hostname,
                        "MetricStat": {
                            "Metric": {
                                "Namespace": "AWS/DynamoDB",
                                "MetricName": metric_name,
                                "Dimensions": dimensions,
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
        content_by_piggyback_hosts: dict[str, list[dict[str, object]]] = {}
        for row in raw_content.content:
            content_by_piggyback_hosts.setdefault(row["Label"], []).append(row)

        key_provisioned_capacity = "ProvisionedThroughput"
        for piggyback_hostname, table in colleague_contents.content.items():
            content_by_piggyback_hosts[piggyback_hostname].append(
                {
                    "provisioned_ReadCapacityUnits": table[key_provisioned_capacity][
                        "ReadCapacityUnits"
                    ],
                    "provisioned_WriteCapacityUnits": table[key_provisioned_capacity][
                        "WriteCapacityUnits"
                    ],
                }
            )

        return AWSComputedContent(content_by_piggyback_hosts, raw_content.cache_timestamp)

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.items()
        ]
