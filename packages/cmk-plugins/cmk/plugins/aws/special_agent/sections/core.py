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

import abc
import re
from collections import defaultdict
from collections.abc import Iterator, Mapping, Sequence
from datetime import datetime
from typing import Any, Literal, NamedTuple, NotRequired, override, TypedDict

from botocore.client import BaseClient
from pydantic import BaseModel

from ..config import AGENT, AWSConfig, LOGGER, RawTags, Tags, TagsImportPatternOption
from ..data_cache import DataCache

NOW = datetime.now()

AWSStrings = bytes | str

Dimension = Mapping[Literal["Name", "Value"], str | None]


class MetricData(TypedDict):
    Namespace: str
    MetricName: str
    Dimensions: Sequence[Dimension]


class MetricStat(TypedDict):
    Metric: MetricData
    Period: int
    Stat: str
    Unit: NotRequired[str]


class MetricRequired(TypedDict):
    Id: str
    Label: str


class Metric(MetricRequired, total=False):
    Expression: str
    MetricStat: MetricStat
    Period: int


Metrics = list[Metric]


class Quota(BaseModel):
    QuotaName: str
    Value: float


def get_seconds_since_midnight(current_time: datetime) -> float:
    midnight = datetime.combine(current_time.date(), datetime.min.time())
    return (current_time - midnight).total_seconds()


def chunks[T](list_: Sequence[T], length: int = 100) -> Sequence[Sequence[T]]:
    return [list_[i : i + length] for i in range(0, len(list_), length)]


def hostname_from_name_and_region(name: str, region: str) -> str:
    """
    We add the region to the the hostname because resources in different regions might have the
    same names (for example replicated DynamoDB tables).
    """
    return f"{name}_{region}"


ResourceTags = Mapping[str, Tags]


def fetch_resource_tags_from_types(
    tagging_client: BaseClient, resource_type_filters: Sequence[str]
) -> ResourceTags:
    """Returns all the resources in the region that have tags.

    This is useful when the service-specific API is not returning tags for every resource as this
    allows you to get all the tags with a single API call rather than calling get_tags for every
    resource.

    For example, the CloudFront APIs don't allow to get tags for all the distributions and the only
    way to have the tags would be to call the `list_tags_for_resource` API for every single
    distribution.
    To prevent that, we can call this method with
    `resource_type_filters=['cloudfront:distribution']` and with the tags you want to filter.

    More info on the format of the resources type on the underlying API call documentation:
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/resourcegroupstaggingapi.html#ResourceGroupsTaggingAPI.Client.get_resources
    """

    tagged_resources = []
    # The get_resource API call has a matching rule (AND) different than the one that we use in
    # checkmk (OR) so we need to fetch all the resources containing tags first and then apply our
    # matching rule.
    # We are calling it with empty `TagFilter` param so get every resource that ever had a tag.
    # For the tags matching rules or other info, look at the documentation of the API call:
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/resourcegroupstaggingapi.html#ResourceGroupsTaggingAPI.Client.get_resources
    for page in tagging_client.get_paginator("get_resources").paginate(
        TagFilters=[],
        ResourceTypeFilters=resource_type_filters,
    ):
        tagged_resources.extend(page.get("ResourceTagMappingList", []))

    return {r["ResourceARN"]: r["Tags"] for r in tagged_resources}


def filter_resources_matching_tags(
    tagged_resources: ResourceTags,
    tags_to_match: Tags,
) -> set[str]:
    """Returns the ARN of all the resources in the region that match **ANY** of the provided tags.

    This is useful when the service-specific API is not returning tags for every resource as this
    allows you to get all the tags with a single API call (e.g., fetch_resource_tags_from_types)
    and filter them with this function.
    """

    if not tags_to_match:
        return set()

    tags_to_match_by_id = defaultdict(set)
    for curr_tag in tags_to_match:
        tags_to_match_by_id[curr_tag["Key"]].add(curr_tag["Value"])

    matching_resources_arn = set()
    for resource_arn, resource_tags in tagged_resources.items():
        is_any_tag_matching = any(
            curr_tag["Key"] in tags_to_match_by_id
            and curr_tag["Value"] in tags_to_match_by_id[curr_tag["Key"]]
            for curr_tag in resource_tags
        )
        if is_any_tag_matching:
            matching_resources_arn.add(resource_arn)
    return matching_resources_arn


class ResultDistributor:
    """
    Mediator which distributes results from sections
    in order to reduce queries to AWS account.
    """

    def __init__(self) -> None:
        self._colleagues: dict[str, list[AWSSection]] = defaultdict(list)

    def add(self, sender_name: str, colleague: AWSSection) -> None:
        self._colleagues[sender_name].append(colleague)

    def distribute(self, sender: AWSSection, result: AWSComputedContent) -> None:
        for colleague in self._colleagues[sender.name]:
            if colleague.name != sender.name:
                colleague.receive(sender, result)


class AWSSectionResults(NamedTuple):
    results: list
    cache_timestamp: float


class AWSSectionResult(NamedTuple):
    piggyback_hostname: AWSStrings
    content: Any
    piggyback_host_labels: Mapping[str, str] | None = None


class AWSLimit(NamedTuple):
    key: AWSStrings
    title: AWSStrings
    limit: int
    amount: int


class AWSRegionLimit(NamedTuple):
    key: AWSStrings
    title: AWSStrings
    limit: int
    amount: int
    region: AWSStrings


class AWSColleagueContents(NamedTuple):
    content: Any
    cache_timestamp: float


class AWSRawContent(NamedTuple):
    content: Any
    cache_timestamp: float


class AWSComputedContent(NamedTuple):
    content: Any
    cache_timestamp: float


class AWSSection(DataCache):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
    ) -> None:
        super().__init__(
            host_name=config.hostname, agent=f"agent_{AGENT}", key=f"{region}-{self.name}"
        )
        self._client = client
        self._region = region
        self._config = config
        self._distributor = ResultDistributor() if distributor is None else distributor
        self._received_results: dict[str, AWSComputedContent] = {}

    @property
    @abc.abstractmethod
    def name(self) -> str:
        pass

    @property
    @abc.abstractmethod
    @override
    def cache_interval(self) -> int:
        """
        In general the default resolution of AWS metrics is 5 min (300 sec)
        The default resolution of AWS S3 metrics is 1 day (86400 sec)
        We use interval property for cached section.
        """
        raise NotImplementedError

    @property
    def region(self) -> str:
        return self._region

    @property
    def granularity(self) -> int:
        """
        The granularity of the returned data in seconds.
        """
        raise NotImplementedError

    @property
    def period(self) -> int:
        return self.validate_period(2 * self.granularity)

    @staticmethod
    def validate_period(period: int, resolution_type: str = "low") -> int:
        """
        What this is all about:
        https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_MetricStat.html
        >>> [AWSSection.validate_period(p, r) for p, r in [(34, "low"), (45, "high"), (120.0, "low")]]
        Traceback (most recent call last):
        ...
        AssertionError: Period must be a multiple of 60 or equal to 1, 5, 10, 30, 60 in case of high resolution.

        >>> AWSSection.validate_period(1234, resolution_type="foo bar")
        Traceback (most recent call last):
            ...
        ValueError: Unknown resolution type: 'foo bar'
        >>> AWSSection.validate_period(120)
        120
        >>> AWSSection.validate_period(30, "high")
        30
        >>> AWSSection.validate_period(180, "high")
        180
        """
        if not isinstance(period, int):
            raise AssertionError(f"Period must be an integer, got {type(period)}.")

        allowed_multiples = 60
        additional_allowed = []

        if resolution_type == "high":
            additional_allowed.extend([1, 5, 10, 30, 60])
        elif resolution_type != "low":
            raise ValueError("Unknown resolution type: '%s'" % resolution_type)

        if not (not period % allowed_multiples or period in additional_allowed):
            raise AssertionError(
                f"Period must be a multiple of {allowed_multiples} or equal to 1, 5, "
                f"10, 30, 60 in case of high resolution."
            )
        return period

    def _send(self, content: AWSComputedContent) -> None:
        self._distributor.distribute(self, content)

    def receive(self, sender: AWSSection, content: AWSComputedContent) -> None:
        self._received_results.setdefault(sender.name, content)

    def run(self, use_cache: bool = False) -> AWSSectionResults:
        colleague_contents = self._get_colleague_contents()

        raw_data = self.get_data(colleague_contents, use_cache=use_cache)
        raw_content = AWSRawContent(
            raw_data,
            self.cache_timestamp
            if (use_cache and self.cache_timestamp is not None)
            else NOW.timestamp(),
        )

        computed_content = self._compute_content(raw_content, colleague_contents)

        self._send(computed_content)
        created_results = self._create_results(computed_content)

        final_results = []
        for result in created_results:
            if not result.content:
                LOGGER.info("%(name)s: Result is empty or None", {"name": self.name})
                continue

            # In the related check plug-in aws.include we parse these results and
            # extend list of json-loaded results, except for labels sections.
            self._validate_result_content(result.content)

            final_results.append(result)
        return AWSSectionResults(final_results, computed_content.cache_timestamp)

    @override
    def get_validity_from_args(self, *args: AWSColleagueContents) -> bool:
        (colleague_contents,) = args
        my_cache_timestamp = self.cache_timestamp
        if my_cache_timestamp is None:
            return False
        if colleague_contents.cache_timestamp > my_cache_timestamp:
            LOGGER.info("Colleague data is newer than cache file %(key)s", {"key": self._key})
            return False
        return True

    @abc.abstractmethod
    def _get_colleague_contents(self) -> AWSColleagueContents:
        """
        Receive section contents from colleagues. The results are stored in
        self._received_results: {<KEY>: AWSComputedContent}.
        The relation between two sections must be declared in the related
        distributor in advance to make this work.
        Use max. cache_timestamp of all received results for
        AWSColleagueContents.cache_timestamp
        """

    @abc.abstractmethod
    @override
    def get_live_data(self, *args):
        """
        Call API methods, eg. 'response = ec2_client.describe_instances()' and
        extract content from raw content.  Raw contents basically consist of
        two sub results:
        - 'ResponseMetadata'
        - '<KEY>'
        Return raw_result['<KEY>'].
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _compute_content(
        self, raw_content: AWSRawContent, colleague_contents: AWSColleagueContents
    ) -> AWSComputedContent:
        """
        Compute the final content of this section based on the raw content of
        this section and the content received from the optional colleague
        sections.
        """

    @abc.abstractmethod
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        pass

    def _get_response_content(self, response, key: str, dflt=None):
        if dflt is None:
            dflt = []
        try:
            return response[key]
        except KeyError:
            LOGGER.info(
                "%(name)s: KeyError; Available keys are %(response)s",
                {"name": self.name, "response": response},
            )
            return dflt

    def _validate_result_content(self, content: list | dict) -> None:
        assert isinstance(content, list), "%s: Result content must be of type 'list'" % self.name

    @staticmethod
    def prepare_tags_for_api_response(tags: RawTags) -> Tags | None:
        """
        We need to change the format, in order to filter out instances with specific
        tags if and only if we already fetched instances, eg. by limits section.
        The format:
        [{'Key': KEY, 'Value': VALUE}, ...]
        """
        if not tags:
            return None
        prepared_tags: Tags = []
        for tag in tags:
            tag_name = tag["Name"]
            tag_key = tag_name[4:] if tag_name.startswith("tag:") else tag_name
            prepared_tags.extend([{"Key": tag_key, "Value": v} for v in tag["Values"]])
        return prepared_tags

    def process_tags_for_cmk_labels(self, tags: Tags) -> Mapping[str, str]:
        """Filter tags that are imported as host/service labels in Checkmk.

        This should not be mixed up with the filtering of services by tags to limit
        the services being created from the agent output.

        By default, all AWS tags are written to the agent output. This function filters
        and transforms the agent output depending on the CLI args given to the agent.
        Inside Checkmk the tags are validated to meet the Checkmk label requirements
        and added as host labels to their respective piggyback host and/or as service
        labels to the respective service using the syntax 'cmk/aws/tag/{key}:{value}'.
        """
        if self._config.tags_option == TagsImportPatternOption.import_all:
            return {tag["Key"]: tag["Value"] for tag in tags}
        if self._config.tags_option == TagsImportPatternOption.ignore_all:
            return {}
        return {
            tag["Key"]: tag["Value"]
            for tag in tags
            if re.search(self._config.tags_option, tag["Key"])
        }


class AWSSectionLimits(AWSSection):
    def __init__(
        self,
        client: BaseClient,
        region: str,
        config: AWSConfig,
        distributor: ResultDistributor | None = None,
        quota_client: BaseClient | None = None,
    ) -> None:
        super().__init__(client, region, config, distributor=distributor)
        self._quota_client = quota_client
        self._limits: dict = {}

    def _add_limit(
        self, piggyback_hostname: str, limit: AWSLimit, region: str | None = None
    ) -> None:
        if region is None:
            region = self._region

        self._limits.setdefault(piggyback_hostname, []).append(
            AWSRegionLimit(
                key=limit.key,
                title=limit.title,
                limit=limit.limit,
                amount=limit.amount,
                region=region,
            )
        )

    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        return [
            AWSSectionResult(piggyback_hostname, limits)
            for piggyback_hostname, limits in self._limits.items()
        ]

    def _iter_service_quotas(self, service_code: str) -> Iterator[Quota]:
        if self._quota_client is None:
            return

        paginator = self._quota_client.get_paginator("list_service_quotas")
        for page in paginator.paginate(ServiceCode=service_code):
            for quota in self._get_response_content(page, "Quotas"):
                yield Quota(**quota)


class AWSSectionLabels(AWSSection):
    @override
    def _create_results(self, computed_content: AWSComputedContent) -> list[AWSSectionResult]:
        assert isinstance(computed_content.content, dict), (
            "%s: Computed result of Labels section must be of type 'dict'" % self.name
        )
        for pb in computed_content.content:
            assert pb, "%s: Piggyback host name is not allowed to be empty" % self.name
        return [
            AWSSectionResult(piggyback_hostname, rows)
            for piggyback_hostname, rows in computed_content.content.items()
        ]

    @override
    def _validate_result_content(self, content: list | dict) -> None:
        assert isinstance(content, dict), "%s: Result content must be of type 'dict'" % self.name


class AWSSectionCloudwatch(AWSSection):
    @override
    def get_live_data(self, *args: AWSColleagueContents) -> Sequence[Mapping[str, object]]:
        (colleague_contents,) = args
        end_time = NOW.timestamp()
        start_time = end_time - self.period
        metric_specs = self._get_metrics(colleague_contents)
        if not metric_specs:
            return []

        # A single GetMetricData call can include up to 100 MetricDataQuery structures
        # There's no pagination for this operation:
        # self._client.can_paginate('get_metric_data') = False
        raw_content = []
        for chunk in chunks(metric_specs):
            if not chunk:
                continue
            response = self._client.get_metric_data(  # type: ignore[attr-defined]
                MetricDataQueries=chunk,
                StartTime=start_time,
                EndTime=end_time,
            )

            metrics = self._get_response_content(response, "MetricDataResults")
            if not metrics:
                continue
            raw_content.extend(metrics)

        self._extend_metrics_by_period(metric_specs, raw_content)

        return raw_content

    @abc.abstractmethod
    def _get_metrics(self, colleague_contents: AWSColleagueContents) -> Metrics:
        pass

    @staticmethod
    def _create_id_for_metric_data_query(index: int, metric_name: str, *args: str) -> str:
        """
        ID field must be unique in a single call.
        The valid characters are letters, numbers, and underscore.
        The first character must be a lowercase letter.
        Regex: ^[a-z][a-zA-Z0-9_]*$
        """
        return "_".join(["id", str(index)] + list(args) + [metric_name])

    def _extend_metrics_by_period(self, metrics: Metrics, raw_content: list) -> None:
        """
        Extend the queried metric values by the corresponding time period. For metrics based on the
        "Sum" statistics, we add the actual time period which can then be used by the check plug-ins
        to compute a rate. For all other metrics, we add 'None', such that the metric values are
        always 2-tuples (value, period), where period is either an actual time period such as 600 s
        or None.
        """
        for metric_specs, metric_contents in zip(metrics, raw_content):
            metric_stat = metric_specs.get("MetricStat", {})
            period = metric_stat["Period"] if metric_stat.get("Stat") == "Sum" else None
            metric_contents["Values"] = [(v, period) for v in metric_contents["Values"]]
