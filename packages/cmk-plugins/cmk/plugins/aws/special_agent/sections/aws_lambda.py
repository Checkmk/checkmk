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

from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from time import sleep
from typing import override, TYPE_CHECKING

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
    Dimension,
    Metrics,
    NOW,
    ResultDistributor,
)

if TYPE_CHECKING:
    from mypy_boto3_logs.client import (  # type: ignore[attr-defined]
        CloudWatchLogsClient,
        GetQueryResultsResponseTypeDef,
        QueryStatusType,
        ResultFieldTypeDef,
    )


ProvisionedConcurrencyConfigs = Mapping[str, Sequence[Mapping[str, str]]]


class LambdaRegionLimits(AWSSectionLimits):
    @property
    @override
    def name(self) -> str:
        return "lambda_region_limits"

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
        return self._client.get_account_settings()  # type: ignore[attr-defined]

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        limits = raw_content.content
        self._add_limit(
            "",
            AWSLimit(
                "total_code_size",
                "Total Code Size",
                100,
                int(limits["AccountLimit"]["TotalCodeSize"]),
            ),
            region=self._region,
        )
        self._add_limit(
            "",
            AWSLimit(
                "concurrent_executions",
                "Concurrent Executions",
                100,
                int(limits["AccountLimit"]["ConcurrentExecutions"]),
            ),
            region=self._region,
        )
        self._add_limit(
            "",
            AWSLimit(
                "unreserved_concurrent_executions",
                "Unreserved Concurrent Executions",
                100,
                int(limits["AccountLimit"]["UnreservedConcurrentExecutions"]),
            ),
            region=self._region,
        )
        return AWSComputedContent(limits, raw_content.cache_timestamp)


class LambdaSummary(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["lambda_names"]
        self._tags = self.prepare_tags_for_api_response(self._config.service_config["lambda_tags"])

    @property
    @override
    def name(self) -> str:
        return "lambda_summary"

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
        return AWSColleagueContents([], 0.0)

    @override
    def get_live_data(self, *args):
        functions = []
        for page in self._client.get_paginator("list_functions").paginate():
            for function in self._get_response_content(page, "Functions"):
                tags = self._get_tagging_for(function.get("FunctionArn"))
                if (
                    self._names is None
                    or (self._names and function.get("FunctionName") in self._names)
                ) and (self._tags is None or self._tags and self._matches_tag_conditions(tags)):
                    function["TagsForCmkLabels"] = self.process_tags_for_cmk_labels(tags)
                    functions.append(function)
        return functions

    def _get_tagging_for(self, function_arn: str) -> Tags:
        tagging = self._get_response_content(self._client.list_tags(Resource=function_arn), "Tags")  # type: ignore[attr-defined]
        # adapt to format of _prepare_tags_for_api_response
        return [{"Key": key, "Value": value} for key, value in tagging.items()]

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
            raw_content.content,
            raw_content.cache_timestamp,
        )

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]


def _function_arn_to_function_name_dim(function_arn: str) -> str:
    """
    >>> _function_arn_to_function_name_dim("arn:aws:lambda:eu-central-1:710145618630:function:my_python_test_function")
    'my_python_test_function'
    """
    return function_arn.split(":")[6]


class LambdaCloudwatch(AWSSectionCloudwatch):
    @property
    @override
    def name(self) -> str:
        return "lambda"

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
        # lambda_provisioned_concurrency has to be used, because some metrics for provisioned concurrency will only
        # be reported if the ARN for the provisioned concurrency configuration is used.
        # lambda_provisioned_concurrency contains also the ARNs for lambda functions without provisioned conurrency.
        colleague = self._received_results.get("lambda_provisioned_concurrency")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    @override
    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        def _get_function_arns(colleague_content: dict) -> Sequence[str]:
            function_arns = []
            for function_arn, provisioned_concurrency_configurations in colleague_content.items():
                for config in provisioned_concurrency_configurations:
                    function_arns.append(config["FunctionArn"])
                function_arns.append(function_arn)
            return function_arns

        def _create_dimensions(function_arn: str) -> Sequence[Dimension]:
            def _function_arn_to_resource_dim(function_arn: str) -> str | None:
                """
                >>> _function_arn_to_resource_dim("arn:aws:lambda:eu-central-1:710145618630:function:my_python_test_function:AliasOrVersionNumber")
                'my_python_test_function:AliasOrVersionNumber'
                """
                splitted = function_arn.split(":")
                return f"{splitted[6]}:{splitted[7]}" if len(splitted) == 8 else None

            dimensions: list[Dimension] = [
                {
                    "Name": "FunctionName",
                    "Value": _function_arn_to_function_name_dim(function_arn),
                }
            ]
            if resource_dim := _function_arn_to_resource_dim(function_arn):
                dimensions.append(
                    {
                        "Name": "Resource",
                        "Value": resource_dim,
                    }
                )
            return dimensions

        metrics = [
            ("ConcurrentExecutions", "Count", "Maximum"),
            ("DeadLetterErrors", "Count", "Sum"),
            ("DestinationDeliveryFailures", "Count", "Sum"),
            ("Duration", "Milliseconds", "Average"),
            ("Errors", "Count", "Sum"),
            ("Invocations", "Count", "Sum"),
            ("IteratorAge", "Count", "Average"),
            ("PostRuntimeExtensionsDuration", "Count", "Average"),
            ("ProvisionedConcurrencyInvocations", "Count", "Sum"),
            ("ProvisionedConcurrencySpilloverInvocations", "Count", "Sum"),
            ("ProvisionedConcurrencyUtilization", "Count", "Average"),
            ("ProvisionedConcurrentExecutions", "Count", "Sum"),
            ("Throttles", "Count", "Sum"),
            ("UnreservedConcurrentExecutions", "Count", "Maximum"),
        ]
        return [
            {
                "Id": self._create_id_for_metric_data_query(idx, metric_name),
                "Label": function_arn,
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/Lambda",
                        "MetricName": metric_name,
                        "Dimensions": _create_dimensions(function_arn),
                    },
                    "Period": self.period,
                    "Stat": stat,
                    "Unit": unit,
                },
            }
            for idx, function_arn in enumerate(_get_function_arns(colleague_contents.content))
            for metric_name, unit, stat in metrics
        ]

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(
            raw_content.content,
            raw_content.cache_timestamp,
        )

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]


class LambdaProvisionedConcurrency(AWSSection):
    @property
    @override
    def name(self) -> str:
        return "lambda_provisioned_concurrency"

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
        colleague = self._received_results.get("lambda_summary")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    def _list_provisioned_concurrency_configs(
        self, function_name: str
    ) -> Sequence[Mapping[str, str]]:
        return [
            config
            for page in self._client.get_paginator("list_provisioned_concurrency_configs").paginate(
                FunctionName=function_name
            )
            for config in self._get_response_content(page, "ProvisionedConcurrencyConfigs")
        ]

    @override
    def get_live_data(self, *args: AWSColleagueContents) -> ProvisionedConcurrencyConfigs:
        (colleague_contents,) = args
        return {
            lambda_function["FunctionArn"]: self._list_provisioned_concurrency_configs(
                lambda_function["FunctionName"]
            )
            for lambda_function in colleague_contents.content
        }

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(
            raw_content.content,
            raw_content.cache_timestamp,
        )

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]

    @override
    def _validate_result_content(self, content: list | dict) -> None:
        assert isinstance(content, dict), "%s: Result content must be of type 'dict'" % self.name


type LambdaMetricStats = Sequence[ResultFieldTypeDef]


class LambdaCloudwatchInsights(AWSSection):
    # The maximum number of log groups that can be queried with a single API call - source:
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/logs.html#CloudWatchLogs.Client.start_query
    MAX_LOG_GROUPS_PER_QUERY = 20

    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._names = self._config.service_config["lambda_names"]
        self._tags = self.prepare_tags_for_api_response(self._config.service_config["lambda_tags"])

    @property
    @override
    def name(self) -> str:
        return "lambda_cloudwatch_insights"

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
        # lambda_provisioned_concurrency has to be used, because some metrics for provisioned concurrency will only
        # be reported if the ARN for the provisioned concurrency configuration is used.
        # lambda_provisioned_concurrency contains also the ARNs for lambda functions without provisioned conurrency.
        colleague = self._received_results.get("lambda_provisioned_concurrency")
        if colleague and colleague.content:
            return AWSColleagueContents(colleague.content, colleague.cache_timestamp)
        return AWSColleagueContents({}, 0.0)

    @staticmethod
    def query_results(
        *,
        client: CloudWatchLogsClient,
        query_id: str,
        timeout_seconds: float,
        sleep_duration: float = 0.5,
    ) -> Sequence[LambdaMetricStats] | None:
        "Synchronous wrapper for asynchronous query API with timeout checking. (agent should not be blocked)."
        response_results: GetQueryResultsResponseTypeDef
        query_start = datetime.now().timestamp()
        status: QueryStatusType = "Scheduled"
        while status != "Complete":
            response_results = client.get_query_results(queryId=query_id)
            status = response_results["status"]
            if datetime.now().timestamp() - query_start >= timeout_seconds:
                client.stop_query(queryId=query_id)
                LOGGER.error(
                    "LambdaCloudwatchInsights: query_results failed"
                    " or timed out with the following results: %(results)s ",
                    {"results": response_results["results"]},
                )
                break
            sleep(sleep_duration)
        # stat metrics are always in the first element of the results or an empty list
        return (
            response_results["results"]
            if response_results["results"] and response_results["status"] == "Complete"
            else None
        )

    def _group_query_results_by_function(
        self, query_results: Sequence[LambdaMetricStats]
    ) -> dict[str, LambdaMetricStats]:
        grouped_results: dict[str, LambdaMetricStats] = {}
        for query_result in query_results:
            if not query_result:
                continue
            log_name = [e["value"] for e in query_result if e["field"] == "@log"][0]
            lambda_fn_name = log_name.split("/")[-1]
            final_query_result = [e for e in query_result if e["field"] != "@log"]
            grouped_results[lambda_fn_name] = final_query_result
        return grouped_results

    def _start_logwatch_query(self, *, log_group_names: list[str], query_string: str) -> str:
        end_time_seconds = int(NOW.timestamp())
        start_time_seconds = int(end_time_seconds - self.period)
        response_query_id = self._client.start_query(  # type: ignore[attr-defined]
            logGroupNames=log_group_names,
            startTime=start_time_seconds,
            endTime=end_time_seconds,
            queryString=query_string,
        )
        return response_query_id["queryId"]

    def _get_splitted_list[T](self, source_list: list[T], chunk_size: int) -> list[list[T]]:
        """
        Split a list into a list of lists where every nested list has a maximum size of `chunk_size`
        """
        return [source_list[i : i + chunk_size] for i in range(0, len(source_list), chunk_size)]

    def _get_all_existing_lambda_log_groups(self) -> set[str]:
        """
        Fetches all the existing log groups in the AWS account that are related to lambda functions
        """
        log_groups: set[str] = set()
        for page in self._client.get_paginator("describe_log_groups").paginate(
            logGroupNamePrefix="/aws/lambda/"
        ):
            log_groups.update(
                e["logGroupName"] for e in self._get_response_content(page, "logGroups")
            )
        return log_groups

    def _get_existing_log_groups_for_functions(self, function_names: Iterable[str]) -> list[str]:
        # We are getting all the existing log groups because we want to query logwatch for multiple
        # log groups at once but the query fails if one of the log groups don't exist so what might
        # happen is that we query log groups for 2 functions: 1 that has an existing log group and 1
        # that doesn't have it, in that case the query fails and we are not getting the data for the
        # function with a log group.
        # To prevent this, we just query the log groups that exists by checking that before doing
        # the actual query.
        all_existing_log_groups = self._get_all_existing_lambda_log_groups()
        functions_log_groups = [f"/aws/lambda/{fn_name}" for fn_name in function_names]
        # `all_existing_log_groups` may contain log groups for lambda functions that don't exist
        # anymore so we are filtering it to just have the log groups for the existing functions
        return [e for e in functions_log_groups if e in all_existing_log_groups]

    @override
    def get_live_data(self, *args: AWSColleagueContents) -> Mapping[str, LambdaMetricStats] | None:
        (colleague_contents,) = args

        function_name_to_arn: dict[str, str] = {
            _function_arn_to_function_name_dim(fn_arn): fn_arn
            for fn_arn in colleague_contents.content
        }
        existing_functions_log_groups = self._get_existing_log_groups_for_functions(
            function_name_to_arn.keys()
        )
        chunked_log_groups: list[list[str]] = self._get_splitted_list(
            existing_functions_log_groups, self.MAX_LOG_GROUPS_PER_QUERY
        )

        queries: list[str] = []
        # Logwatch queries are async jobs so we are first starting all of them and then getting the
        # result for all of them so that they will be processed in parallel by AWS
        for curr_log_groups in chunked_log_groups:
            query_id = self._start_logwatch_query(
                log_group_names=curr_log_groups,
                query_string='filter @type = "REPORT"'
                "| stats "
                "max(@maxMemoryUsed) as max_memory_used_bytes,"
                "max(@initDuration) as max_init_duration_ms,"
                'sum(strcontains(@message, "Init Duration")) as count_cold_starts,'
                "count() as count_invocations "
                "by @log",
            )
            queries.append(query_id)

        cloudwatch_data: dict[str, LambdaMetricStats] = {}
        for query_id in queries:
            query_results = self.query_results(
                client=self._client,  # type: ignore[arg-type]
                query_id=query_id,
                timeout_seconds=60,
            )
            if not query_results:
                continue
            current_data = self._group_query_results_by_function(query_results)
            for fn_name, fn_stats in current_data.items():
                fn_arn = function_name_to_arn[fn_name]
                cloudwatch_data[fn_arn] = fn_stats
        return cloudwatch_data

    @override
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        return AWSComputedContent(
            raw_content.content,
            raw_content.cache_timestamp,
        )

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [AWSSectionResult("", computed_content.content)]

    @override
    def _validate_result_content(self, content: list | dict) -> None:
        assert isinstance(content, dict), "%s: Result content must be of type 'dict'" % self.name
