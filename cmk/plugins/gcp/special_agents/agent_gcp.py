#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs
import datetime
import json
import sys
import time
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from functools import cache
from types import TracebackType
from typing import Any, assert_never, Protocol, Self

import google.protobuf.duration_pb2 as duration
from google.api_core.exceptions import InvalidArgument, PermissionDenied, Unauthenticated
from google.auth.exceptions import MalformedError
from google.cloud import asset_v1, monitoring_v3
from google.cloud.monitoring_v3.types import Aggregation as GoogleAggregation
from google.cloud.monitoring_v3.types import TimeSeries
from google.oauth2 import service_account
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError
from googleapiclient.http import HttpRequest

from cmk.plugins.gcp.lib.constants import Extractors
from cmk.special_agents.v0_unstable.agent_common import (
    ConditionalPiggybackSection,
    SectionWriter,
    special_agent_main,
)
from cmk.special_agents.v0_unstable.argument_parsing import Args, create_default_argument_parser

# Those are enum classes defined in the Aggregation class. Not nice but works
Aligner = GoogleAggregation.Aligner
Reducer = GoogleAggregation.Reducer

####################
# Type Definitions #
####################


@dataclass(frozen=True)
class Asset:
    asset: asset_v1.Asset

    # TODO(rs): replace static with normal: def serialize(self) -> str:
    @staticmethod
    def serialize(obj: "Asset") -> str:
        return json.dumps(asset_v1.Asset.to_dict(obj.asset))

    @classmethod
    def deserialize(cls, data: str) -> Self:
        asset = asset_v1.Asset.from_json(data)
        return cls(asset=asset)  # type: ignore[arg-type]


Schema = Sequence[Mapping[str, str]]
Page = Sequence[Mapping[str, Sequence[Mapping[str, str]]]]
Pages = Sequence[Page]


class ClientProtocol(Protocol):
    date: datetime.date  # date when client is executed

    @property
    def project(self) -> str: ...

    def list_time_series(self, request: Any) -> Iterable[TimeSeries]: ...

    def list_assets(self, request: Any) -> Iterable[asset_v1.Asset]: ...

    def list_costs(self, tableid: str) -> tuple[Schema, Pages]: ...


@dataclass(unsafe_hash=True)
class Client:
    account_info: dict[str, str] = field(compare=False)
    project: str
    date: datetime.date

    @cache
    def monitoring(self) -> monitoring_v3.MetricServiceClient:
        return monitoring_v3.MetricServiceClient.from_service_account_info(self.account_info)

    @cache
    def asset(self) -> asset_v1.AssetServiceClient:
        return asset_v1.AssetServiceClient.from_service_account_info(self.account_info)

    @cache
    def bigquery(self) -> Resource:
        credentials = service_account.Credentials.from_service_account_info(self.account_info)
        scopes = ["https://www.googleapis.com/auth/bigquery.readonly"]
        scoped_credentials = credentials.with_scopes(list(scopes))
        service = build("bigquery", "v2", credentials=scoped_credentials)
        return service.jobs()

    def list_time_series(self, request: Any) -> Iterable[TimeSeries]:
        return self.monitoring().list_time_series(request)

    def list_assets(self, request: Any) -> Iterable[asset_v1.Asset]:
        return self.asset().list_assets(request)

    def list_costs(self, tableid: str) -> tuple[Schema, Pages]:
        first_of_month = self.date.replace(day=1)
        if "`" in tableid:
            raise ValueError("tableid contains invalid character")

        # the query is based on a example query from the official docs:
        # https://cloud.google.com/billing/docs/how-to/export-data-bigquery-tables/standard-usage#sum-costs-per-invoice
        # table id is similar to: <project_id>.<dataset_id>.gcp_billing_export_v1_<billing_account_id>
        query = (
            "SELECT "  # nosec B608 # BNS:d840de
            "project.name, "
            "project.id, "
            "(SUM(CAST(cost AS NUMERIC)) + SUM(IFNULL((SELECT SUM(CAST(c.amount AS NUMERIC)) FROM UNNEST(credits) c), 0))) AS cost, "
            "currency, "
            "invoice.month "
            f"FROM `{tableid}`"
            f'WHERE invoice.month = "{first_of_month.strftime("%Y%m")}" '
            f'AND DATE(_PARTITIONTIME) >= "{first_of_month.strftime("%Y-%m-%d")}" '
            "AND project.name IS NOT NULL "
            "GROUP BY project.name, project.id, currency, invoice.month "
            "ORDER BY project.name, invoice.month"
        )

        body = {"query": query, "useLegacySql": False}
        request: HttpRequest = self.bigquery().query(projectId=self.project, body=body)  # type: ignore[attr-defined]
        response = request.execute()
        schema: Schema = response["schema"]["fields"]

        pages: list[Page] = [response["rows"]]
        # collect all rows, even if we use pagination
        if "pageToken" in response:
            request = self.bigquery().getQueryResults(  # type: ignore[attr-defined]
                projectId=self.project,
                jobId=response["jobReference"]["jobId"],
                location=response["jobReference"]["location"],
                pageToken=response["pageToken"],
            )
            response = request.execute()
            pages.append(response["rows"])

            while next_request := self.bigquery().getQueryResults_next(request, response):  # type: ignore[attr-defined]
                next_response = next_request.execute()
                request = next_request
                response = next_response
                pages.append(response["rows"])

        return schema, pages


@dataclass(frozen=True)
class Aggregation:
    # Those are of from the enum Aligner and Reducer. MyPy cannot handle those imports
    per_series_aligner: int
    cross_series_reducer: int = Reducer.REDUCE_SUM
    alignment_period: int = 60
    group_by_fields: Sequence[str] = field(default_factory=list)

    def to_obj(self, default_groupby: str) -> GoogleAggregation:
        groupbyfields = [default_groupby]
        groupbyfields.extend(self.group_by_fields)
        # TODO(rs): code below is breaking typing, fixit, please
        return GoogleAggregation(
            {
                "alignment_period": duration.Duration(seconds=self.alignment_period),
                "group_by_fields": groupbyfields,
                "per_series_aligner": self.per_series_aligner,
                "cross_series_reducer": self.cross_series_reducer,
            }
        )


@dataclass(frozen=True)
class Metric:
    name: str
    aggregation: Aggregation

    def request(
        self, interval: monitoring_v3.TimeInterval, groupby: str, project: str
    ) -> Mapping[str, Any]:
        return {
            "name": f"projects/{project}",
            "filter": f'metric.type = "{self.name}"',
            "interval": interval,
            "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
            "aggregation": self.aggregation.to_obj(groupby),
        }


@dataclass(frozen=True)
class Service:
    metrics: Sequence[Metric]
    name: str
    default_groupby: str


# todo: Do I want to have a class that automatically prepends gcp?
Labels = Mapping[str, str]


@dataclass(frozen=True)
class HostLabelSection:
    labels: Labels
    name: str = "labels"


class PiggyBackService:
    """
    How are piggy back hosts determined?

    asset_label: str,
    Is used to get the UID for a host from assets that we can look for in the metrics

    metric_label: str,
    Is used to get the host UID from a metric and filter metrics according to hosts

    name_label: str,
    Used to determine host name from asset information. Does not need to equal asset_label
    """

    def __init__(
        self,
        name: str,
        asset_type: str,
        # used to identify marker for host from asset information
        asset_label: str,
        # used to identify timeseries for a host
        metric_label: str,
        # used to determine host name from asset information. Does not need to equal asset_label
        name_label: str,
        labeler: Callable[[Asset], HostLabelSection],
        services: Sequence[Service],
    ):
        self.name = name
        self.asset_type = asset_type
        self.labeler = labeler
        self.services = services
        self.asset_label = asset_label
        self.metric_label = metric_label
        self.name_label = name_label


@dataclass(frozen=True)
class Result:
    ts: TimeSeries
    aggregation: GoogleAggregation

    # TODO(rs): replace static with normal: def serialize(self) -> str:
    @staticmethod
    def serialize(obj: "Result") -> str:
        aggregation = {
            "alignment_period": {"seconds": int(obj.aggregation.alignment_period.seconds)},
            "group_by_fields": list(obj.aggregation.group_by_fields),
            "per_series_aligner": obj.aggregation.per_series_aligner.value,
            "cross_series_reducer": obj.aggregation.cross_series_reducer.value,
        }
        return json.dumps({"ts": TimeSeries.to_dict(obj.ts), "aggregation": aggregation})

    @classmethod
    def deserialize(cls, data: str) -> "Result":
        deserialized = json.loads(data)
        ts = TimeSeries.from_json(json.dumps(deserialized["ts"]))
        raw_aggregation = deserialized["aggregation"]

        aggregation = GoogleAggregation(
            alignment_period=duration.Duration(seconds=60),
            group_by_fields=raw_aggregation["group_by_fields"],
            per_series_aligner=raw_aggregation["per_series_aligner"],
            cross_series_reducer=raw_aggregation["cross_series_reducer"],
        )
        return cls(ts=ts, aggregation=aggregation)  # type: ignore[arg-type]


@dataclass(frozen=True)
class AssetSection:
    name: str
    assets: Sequence[Asset]
    config: Sequence[str]


@dataclass(frozen=True)
class ResultSection:
    name: str
    results: Sequence[Result]


@dataclass(frozen=True)
class PiggyBackSection:
    name: str
    service_name: str
    labels: HostLabelSection
    sections: Iterator[ResultSection]


@dataclass(frozen=True)
class CostRow:
    project: str
    id: str
    month: str
    amount: float
    currency: str

    @staticmethod
    def serialize(row: "CostRow") -> str:
        return json.dumps(
            {
                "project": row.project,
                "id": row.id,
                "month": row.month,
                "amount": row.amount,
                "currency": row.currency,
            }
        )


@dataclass(frozen=True)
class CostSection:
    rows: Sequence[CostRow]
    query_date: datetime.date
    name: str = "cost"


@dataclass(frozen=True)
class ExceptionSection:
    exc_type: type[BaseException] | None
    exception: BaseException | None
    traceback: TracebackType | None
    name: str = "exception"
    source: str | None = ""

    def serialize(self) -> str | None:
        if self.exc_type is None:
            return None
        return f"{self.exc_type.__name__}:{self.source}:{self.exception}".replace("\n", "")


Section = (
    AssetSection
    | ResultSection
    | PiggyBackSection
    | CostSection
    | ExceptionSection
    | HostLabelSection
)

#################
# Serialization #
#################


def _asset_serializer(section: AssetSection) -> None:
    with SectionWriter("gcp_assets") as w:
        w.append(json.dumps({"config": section.config}))
        for a in section.assets:
            w.append(Asset.serialize(a))


def _result_serializer(section: ResultSection) -> None:
    with SectionWriter(f"gcp_service_{section.name}") as w:
        for r in section.results:
            w.append(Result.serialize(r))


def _piggyback_serializer(section: PiggyBackSection) -> None:
    with ConditionalPiggybackSection(section.name):
        _label_serializer(section.labels)
        for s in section.sections:
            new_s = ResultSection(f"{section.service_name}_{s.name}", s.results)
            _result_serializer(new_s)


def _cost_serializer(section: CostSection) -> None:
    with SectionWriter("gcp_cost") as w:
        w.append(json.dumps({"query_month": section.query_date.strftime("%Y%m")}))
        for row in section.rows:
            w.append(CostRow.serialize(row))


def _exception_serializer(section: ExceptionSection) -> None:
    with SectionWriter("gcp_exceptions") as w:
        if section.exc_type is not None:
            w.append(section.serialize())


def _label_serializer(section: HostLabelSection) -> None:
    with SectionWriter("labels") as w:
        w.append(json.dumps(section.labels))


def gcp_serializer(sections: Iterable[Section]) -> None:
    for section in sections:
        if isinstance(section, AssetSection):
            _asset_serializer(section)
        elif isinstance(section, ResultSection):
            _result_serializer(section)
        elif isinstance(section, PiggyBackSection):
            _piggyback_serializer(section)
        elif isinstance(section, CostSection):
            _cost_serializer(section)
        elif isinstance(section, ExceptionSection):
            _exception_serializer(section)
        elif isinstance(section, HostLabelSection):
            _label_serializer(section)
        else:
            assert_never(section)


###########
# Metrics #
###########


@dataclass(frozen=True)
class ResourceFilter:
    label: str
    value: str


def _filter_result_sections(
    sections: Iterable[ResultSection],
    filter_by: ResourceFilter,
) -> Iterator[ResultSection]:
    yield from (
        ResultSection(
            name=result.name,
            results=filtered_results,
        )
        for result in sections
        if (
            filtered_results := [
                ts_result
                for ts_result in result.results
                if ts_result.ts.resource.labels[filter_by.label] == filter_by.value
            ]
        )
    )


def time_series(client: ClientProtocol, service: Service) -> Sequence[Result]:
    now = time.time()
    seconds = int(now)
    nanos = int((now - seconds) * 10**9)
    # request data up to 4.5 minutes in the past. Typical sampling interval for metrics we use is 60 seconds. However, it can take up to
    # 3.5 min (210s) for data to be available. Given the standard agent update time of 1 minute, this setting ensures we see any given value at
    # least once. A downside of this approach is that a stale value would still be used by cmk for up to 4 minutes 40 seconds. A value is considered
    # stale if no data point is stored in GCP in the last sampling interval.
    # See GCP docs for definitions of metric data availability
    # https://cloud.google.com/monitoring/api/metrics_gcp
    interval = monitoring_v3.TimeInterval(
        {
            "end_time": {"seconds": seconds, "nanos": nanos},
            "start_time": {"seconds": (seconds - 280), "nanos": nanos},
        }
    )
    ts_results: list[Result] = []
    for metric in service.metrics:
        request = metric.request(interval, groupby=service.default_groupby, project=client.project)
        try:
            results = client.list_time_series(request=request)
        except PermissionDenied:
            raise
        except Exception as e:
            # 429 is a rate limit error (429 Query aborted. Please reduce the query rate.).
            # We want to catch this and continue with the next metric
            if "429" in str(e):
                exc_type, exception, traceback = sys.exc_info()
                gcp_serializer(
                    [
                        ExceptionSection(
                            exc_type,
                            exception,
                            traceback,
                            source=f"Metric: {metric.name}",
                        )
                    ]
                )
                continue
            raise RuntimeError(metric.name) from e

        for ts in results:
            result = Result(
                ts=ts,
                aggregation=metric.aggregation.to_obj(service.default_groupby),
            )
            ts_results.append(result)

    return ts_results


def run_metrics(client: ClientProtocol, services: Iterable[Service]) -> Iterator[ResultSection]:
    for s in services:
        yield ResultSection(s.name, time_series(client, s))


################################
# Asset Information collection #
################################


def gather_assets(client: ClientProtocol) -> Sequence[Asset]:
    request = asset_v1.ListAssetsRequest(
        parent=f"projects/{client.project}",
        content_type=asset_v1.ContentType.RESOURCE,
        asset_types=list(Extractors),
    )
    all_assets = client.list_assets(request)
    return [Asset(a) for a in all_assets]


def run_assets(client: ClientProtocol, config: Sequence[str]) -> AssetSection:
    return AssetSection("asset", gather_assets(client), config)


##############
# piggy back #
##############


def piggy_back(
    client: ClientProtocol,
    service: PiggyBackService,
    assets: Sequence[Asset],
    prefix: str,
) -> Iterable[PiggyBackSection]:
    sections = list(run_metrics(client, services=service.services))

    for host in [a for a in assets if a.asset.asset_type == service.asset_type]:
        label = host.asset.resource.data[service.asset_label]
        name = f"{prefix}_{host.asset.resource.data[service.name_label]}"
        assert isinstance(label, str)  # hint for mypy

        filter_by = ResourceFilter(label=service.metric_label, value=label)
        filtered_sections = _filter_result_sections(sections, filter_by)
        yield PiggyBackSection(
            name=name,
            service_name=service.name,
            labels=HostLabelSection(
                labels=dict(service.labeler(host).labels) | {"cmk/gcp/projectId": client.project}
            ),
            sections=filtered_sections,
        )


def run_piggy_back(
    client: ClientProtocol,
    services: Sequence[PiggyBackService],
    assets: Sequence[Asset],
    prefix: str,
) -> Iterable[PiggyBackSection]:
    for s in services:
        yield from piggy_back(client, s, assets, prefix)


########
# cost #
########
@dataclass(frozen=True)
class CostArgument:
    tableid: str


def gather_costs(client: ClientProtocol, cost: CostArgument) -> Sequence[CostRow]:
    schema, pages = client.list_costs(tableid=cost.tableid)
    columns = {el["name"]: i for i, el in enumerate(schema)}
    assert set(columns.keys()) == {"name", "id", "cost", "currency", "month"}
    cost_rows: list[CostRow] = []
    for page in pages:
        for row in page:
            data = row["f"]
            cost_rows.append(
                CostRow(
                    project=data[columns["name"]]["v"],
                    id=data[columns["id"]]["v"],
                    month=data[columns["month"]]["v"],
                    amount=float(data[columns["cost"]]["v"]),
                    currency=data[columns["currency"]]["v"],
                )
            )
    return cost_rows


def run_cost(client: ClientProtocol, cost: CostArgument | None) -> Iterable[CostSection]:
    if cost is None:
        return
    yield CostSection(rows=gather_costs(client, cost), query_date=client.date)


#################
# Orchestration #
#################


def run(
    client: ClientProtocol,
    services: Sequence[Service],
    piggy_back_services: Sequence[PiggyBackService],
    serializer: Callable[[Iterable[Section] | Iterable[PiggyBackSection]], None],
    cost: CostArgument | None,
    piggy_back_prefix: str,
) -> None:
    serializer([HostLabelSection(labels={"cmk/gcp/projectId": client.project})])
    try:
        assets = run_assets(
            client, [s.name for s in services] + [s.name for s in piggy_back_services]
        )
        serializer([assets])
    except (PermissionDenied, Unauthenticated):
        exc_type, exception, traceback = sys.exc_info()
        serializer([ExceptionSection(exc_type, exception, traceback, source="Cloud Asset")])
        return

    try:
        serializer(run_metrics(client, services))
        serializer(run_piggy_back(client, piggy_back_services, assets.assets, piggy_back_prefix))
    except (PermissionDenied, Unauthenticated):
        exc_type, exception, traceback = sys.exc_info()
        serializer([ExceptionSection(exc_type, exception, traceback, source="Monitoring")])
        return

    try:
        serializer(run_cost(client, cost))
    except HttpError:
        exc_type, exception, traceback = sys.exc_info()
        serializer([ExceptionSection(exc_type, exception, traceback, source="BigQuery")])
        return

    serializer([ExceptionSection(None, None, None)])


#######################################################################
# Configuration of which metrics we collect for a service starts here #
#                                                                     #
# A list of all available metrics can be found here:                  #
# https://cloud.google.com/monitoring/api/metrics_gcp                 #
#######################################################################


GCS = Service(
    name="gcs",
    default_groupby="resource.bucket_name",
    metrics=[
        Metric(
            name="storage.googleapis.com/api/request_count",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_RATE,
            ),
        ),
        Metric(
            name="storage.googleapis.com/network/sent_bytes_count",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_RATE,
            ),
        ),
        Metric(
            name="storage.googleapis.com/network/received_bytes_count",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_RATE,
            ),
        ),
        Metric(
            name="storage.googleapis.com/storage/total_bytes",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MEAN,
            ),
        ),
        Metric(
            name="storage.googleapis.com/storage/object_count",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MEAN,
            ),
        ),
    ],
)


FUNCTIONS = Service(
    name="cloud_functions",
    default_groupby="resource.function_name",
    metrics=[
        Metric(
            name="cloudfunctions.googleapis.com/function/execution_count",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_RATE,
            ),
        ),
        Metric(
            name="cloudfunctions.googleapis.com/function/network_egress",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_RATE,
            ),
        ),
        Metric(
            name="cloudfunctions.googleapis.com/function/user_memory_bytes",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_PERCENTILE_50,
            ),
        ),
        Metric(
            name="cloudfunctions.googleapis.com/function/user_memory_bytes",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_PERCENTILE_95,
            ),
        ),
        Metric(
            name="cloudfunctions.googleapis.com/function/user_memory_bytes",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_PERCENTILE_99,
            ),
        ),
        Metric(
            name="cloudfunctions.googleapis.com/function/instance_count",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MAX,
            ),
        ),
        Metric(
            name="cloudfunctions.googleapis.com/function/execution_times",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_PERCENTILE_50,
            ),
        ),
        Metric(
            name="cloudfunctions.googleapis.com/function/execution_times",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_PERCENTILE_95,
            ),
        ),
        Metric(
            name="cloudfunctions.googleapis.com/function/execution_times",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_PERCENTILE_99,
            ),
        ),
        Metric(
            name="cloudfunctions.googleapis.com/function/active_instances",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MAX,
            ),
        ),
    ],
)


RUN = Service(
    name="cloud_run",
    default_groupby="resource.service_name",
    metrics=[
        Metric(
            name="run.googleapis.com/container/memory/utilizations",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_PERCENTILE_50,
            ),
        ),
        Metric(
            name="run.googleapis.com/container/memory/utilizations",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_PERCENTILE_95,
            ),
        ),
        Metric(
            name="run.googleapis.com/container/memory/utilizations",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_PERCENTILE_99,
            ),
        ),
        Metric(
            name="run.googleapis.com/container/network/received_bytes_count",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_RATE,
            ),
        ),
        Metric(
            name="run.googleapis.com/container/network/sent_bytes_count",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_RATE,
            ),
        ),
        Metric(
            name="run.googleapis.com/request_count",
            # TODO get by different status codes
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_RATE,
                group_by_fields=["metric.response_code_class"],
            ),
        ),
        Metric(
            name="run.googleapis.com/container/cpu/utilizations",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_PERCENTILE_50,
            ),
        ),
        Metric(
            name="run.googleapis.com/container/cpu/utilizations",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_PERCENTILE_95,
            ),
        ),
        Metric(
            name="run.googleapis.com/container/cpu/utilizations",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_PERCENTILE_99,
            ),
        ),
        Metric(
            name="run.googleapis.com/container/billable_instance_time",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_RATE,
            ),
        ),
        Metric(
            name="run.googleapis.com/container/instance_count",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MAX,
            ),
        ),
        Metric(
            name="run.googleapis.com/request_latencies",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_PERCENTILE_50,
                group_by_fields=["metric.response_code_class"],
            ),
        ),
        Metric(
            name="run.googleapis.com/request_latencies",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_PERCENTILE_95,
                group_by_fields=["metric.response_code_class"],
            ),
        ),
        Metric(
            name="run.googleapis.com/request_latencies",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_PERCENTILE_99,
                group_by_fields=["metric.response_code_class"],
            ),
        ),
    ],
)

CLOUDSQL = Service(
    name="cloud_sql",
    default_groupby="resource.database_id",
    metrics=[
        Metric(
            name="cloudsql.googleapis.com/database/up",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MAX,
            ),
        ),
        Metric(
            name="cloudsql.googleapis.com/database/network/received_bytes_count",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_RATE,
            ),
        ),
        Metric(
            name="cloudsql.googleapis.com/database/network/sent_bytes_count",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_RATE,
            ),
        ),
        Metric(
            name="cloudsql.googleapis.com/database/network/connections",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MAX,
            ),
        ),
        Metric(
            name="cloudsql.googleapis.com/database/memory/utilization",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MAX,
            ),
        ),
        Metric(
            name="cloudsql.googleapis.com/database/cpu/utilization",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MAX,
            ),
        ),
        Metric(
            name="cloudsql.googleapis.com/database/state",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_NEXT_OLDER,
                cross_series_reducer=Reducer.REDUCE_NONE,
            ),
        ),
        Metric(
            name="cloudsql.googleapis.com/database/disk/write_ops_count",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_RATE,
            ),
        ),
        Metric(
            name="cloudsql.googleapis.com/database/disk/read_ops_count",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_RATE,
            ),
        ),
        Metric(
            name="cloudsql.googleapis.com/database/disk/utilization",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MAX,
            ),
        ),
        Metric(
            name="cloudsql.googleapis.com/database/disk/bytes_used",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MAX,
            ),
        ),
        Metric(
            name="cloudsql.googleapis.com/database/disk/quota",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MAX,
            ),
        ),
        Metric(
            name="cloudsql.googleapis.com/database/replication/replica_lag",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MAX,
            ),
        ),
    ],
)

FILESTORE = Service(
    name="filestore",
    default_groupby="resource.instance_name",
    metrics=[
        Metric(
            name="file.googleapis.com/nfs/server/used_bytes_percent",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MAX,
            ),
        ),
        Metric(
            name="file.googleapis.com/nfs/server/write_ops_count",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_RATE,
            ),
        ),
        Metric(
            name="file.googleapis.com/nfs/server/read_ops_count",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_RATE,
            ),
        ),
        Metric(
            name="file.googleapis.com/nfs/server/average_read_latency",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MAX,
            ),
        ),
        Metric(
            name="file.googleapis.com/nfs/server/average_write_latency",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MAX,
            ),
        ),
        Metric(
            name="file.googleapis.com/nfs/server/free_bytes",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MAX,
            ),
        ),
        Metric(
            name="file.googleapis.com/nfs/server/used_bytes",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MAX,
            ),
        ),
    ],
)

REDIS = Service(
    name="redis",
    default_groupby="resource.instance_id",
    metrics=[
        Metric(
            name="redis.googleapis.com/stats/cpu_utilization",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MAX,
            ),
        ),
        Metric(
            name="redis.googleapis.com/stats/memory/usage_ratio",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MAX,
            ),
        ),
        Metric(
            name="redis.googleapis.com/stats/memory/system_memory_usage_ratio",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MAX,
            ),
        ),
        Metric(
            name="redis.googleapis.com/stats/evicted_keys",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MAX,
            ),
        ),
        Metric(
            name="redis.googleapis.com/stats/cache_hit_ratio",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MAX,
            ),
        ),
        Metric(
            name="redis.googleapis.com/clients/connected",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MAX,
            ),
        ),
        Metric(
            name="redis.googleapis.com/stats/connections/total",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_RATE,
            ),
        ),
        Metric(
            name="redis.googleapis.com/stats/reject_connections_count",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_RATE,
            ),
        ),
        Metric(
            name="redis.googleapis.com/clients/blocked",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MAX,
            ),
        ),
        Metric(
            name="redis.googleapis.com/replication/master/slaves/lag",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MAX,
                group_by_fields=["metric.slave"],
            ),
        ),
        Metric(
            name="redis.googleapis.com/replication/role",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MAX,
                group_by_fields=["resource.node_id"],
            ),
        ),
    ],
)

GCE_STORAGE = Service(
    name="gce_storage",
    default_groupby="metric.device_name",
    metrics=[
        Metric(
            name="compute.googleapis.com/instance/disk/read_bytes_count",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_SUM,
            ),
        ),
        Metric(
            name="compute.googleapis.com/instance/disk/read_ops_count",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_SUM,
            ),
        ),
        Metric(
            name="compute.googleapis.com/instance/disk/write_bytes_count",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_SUM,
            ),
        ),
        Metric(
            name="compute.googleapis.com/instance/disk/write_ops_count",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_SUM,
            ),
        ),
    ],
)

HTTP_LOADBALANCER = Service(
    name="http_lb",
    # this is shown as a "load balancer" in the cloud console
    default_groupby="resource.url_map_name",
    metrics=[
        Metric(
            name="loadbalancing.googleapis.com/https/total_latencies",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_PERCENTILE_50,
            ),
        ),
        Metric(
            name="loadbalancing.googleapis.com/https/total_latencies",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_PERCENTILE_95,
            ),
        ),
        Metric(
            name="loadbalancing.googleapis.com/https/total_latencies",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_PERCENTILE_99,
            ),
        ),
        Metric(
            name="loadbalancing.googleapis.com/https/request_count",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_SUM,
            ),
        ),
    ],
)


def default_labeler(asset: Asset) -> HostLabelSection:
    if "labels" in asset.asset.resource.data:
        labels = asset.asset.resource.data["labels"]
        if isinstance(labels, Mapping):
            return HostLabelSection(labels={f"cmk/gcp/labels/{k}": v for k, v in labels.items()})
        # data are malformed, we have to break
        raise RuntimeError(f"Invalid data type asset.asset.resource.data: '{type(labels)}'")

    return HostLabelSection(labels={})


def gce_labeler(asset: Asset) -> HostLabelSection:
    # TODO(rs): replace creative code below with something we could understand and statically test
    return HostLabelSection(labels={**default_labeler(asset).labels, "cmk/gcp/gce": "instance"})


GCE = PiggyBackService(
    name="gce",
    asset_type="compute.googleapis.com/Instance",
    asset_label="id",
    metric_label="instance_id",
    name_label="name",
    labeler=gce_labeler,
    services=[
        Service(
            name="uptime_total",
            default_groupby="resource.instance_id",
            metrics=[
                Metric(
                    name="compute.googleapis.com/instance/uptime_total",
                    aggregation=Aggregation(
                        per_series_aligner=Aligner.ALIGN_MAX,
                    ),
                )
            ],
        ),
        Service(
            name="disk",
            default_groupby="resource.instance_id",
            metrics=[
                Metric(
                    name="compute.googleapis.com/instance/disk/read_bytes_count",
                    aggregation=Aggregation(
                        per_series_aligner=Aligner.ALIGN_SUM,
                    ),
                ),
                Metric(
                    name="compute.googleapis.com/instance/disk/read_ops_count",
                    aggregation=Aggregation(
                        per_series_aligner=Aligner.ALIGN_SUM,
                    ),
                ),
                Metric(
                    name="compute.googleapis.com/instance/disk/write_bytes_count",
                    aggregation=Aggregation(
                        per_series_aligner=Aligner.ALIGN_SUM,
                    ),
                ),
                Metric(
                    name="compute.googleapis.com/instance/disk/write_ops_count",
                    aggregation=Aggregation(
                        per_series_aligner=Aligner.ALIGN_SUM,
                    ),
                ),
            ],
        ),
        Service(
            name="cpu",
            default_groupby="resource.instance_id",
            metrics=[
                Metric(
                    name="compute.googleapis.com/instance/cpu/utilization",
                    aggregation=Aggregation(per_series_aligner=Aligner.ALIGN_MAX),
                ),
                Metric(
                    name="compute.googleapis.com/instance/cpu/reserved_cores",
                    aggregation=Aggregation(per_series_aligner=Aligner.ALIGN_MAX),
                ),
            ],
        ),
        Service(
            name="network",
            default_groupby="resource.instance_id",
            metrics=[
                Metric(
                    name="compute.googleapis.com/instance/network/received_bytes_count",
                    aggregation=Aggregation(per_series_aligner=Aligner.ALIGN_RATE),
                ),
                Metric(
                    name="compute.googleapis.com/instance/network/sent_bytes_count",
                    aggregation=Aggregation(per_series_aligner=Aligner.ALIGN_RATE),
                ),
            ],
        ),
    ],
)

SERVICES = {
    s.name: s
    for s in [
        GCS,
        FUNCTIONS,
        RUN,
        CLOUDSQL,
        FILESTORE,
        REDIS,
        GCE_STORAGE,
        HTTP_LOADBALANCER,
    ]
}
PIGGY_BACK_SERVICES = {s.name: s for s in [GCE]}


def parse_arguments(argv: Sequence[str] | None) -> Args:
    parser = create_default_argument_parser(description=__doc__)
    parser.add_argument("--project", type=str, help="Global ID of Project", required=True)
    parser.add_argument(
        "--credentials",
        type=str,
        help="JSON credentials for service account",
        required=True,
    )
    parser.add_argument(
        "--cost_table",
        type=str,
        help="Enable cost monitoring using specified big query table. Give full table id",
        required=False,
    )
    parser.add_argument(
        "--date",
        type=datetime.date.fromisoformat,
        help="date when agent was executed in iso format",
        required=False,
    )
    parser.add_argument(
        "--services",
        nargs="+",
        action="extend",
        help=f"implemented services: {','.join(list(SERVICES))}",
        choices=list(SERVICES) + list(PIGGY_BACK_SERVICES),
        required=False,
        default=[],
    )
    parser.add_argument(
        "--piggy-back-prefix",
        type=str,
        help="Prefix for piggyback hosts",
        required=True,
    )
    parser.add_argument(
        "--connection-test",
        action="store_true",
        help="Run a connection test. No further agent code is executed.",
    )
    return parser.parse_args(argv)


def _test_connection(args: Args) -> int:
    try:
        client = Client(json.loads(args.credentials), args.project, args.date)
        request = asset_v1.ListAssetsRequest(
            parent=f"projects/{client.project}",
            content_type=asset_v1.ContentType.RESOURCE,
            asset_types=list(Extractors),
        )
        client.list_assets(request)
        return 0
    except json.decoder.JSONDecodeError as exc:
        error_msg = f"Connection failed when trying to decode the provided JSON: {exc}\n"
        sys.stderr.write(error_msg)
        return 2
    # TODO: This list of exception types is probably not exhaustive and should be extended after
    #       thorough debugging of the GCP connection test
    except (
        Unauthenticated,
        InvalidArgument,
        MalformedError,
        PermissionDenied,
        ValueError,
    ) as exc:
        error_msg = f"Connection failed with: {exc}\n"
        sys.stderr.write(error_msg)
        return 2
    return 0


def agent_gcp_main(args: Args) -> int:
    if args.connection_test:
        return _test_connection(args)

    client = Client(json.loads(args.credentials), args.project, args.date)
    services = [SERVICES[s] for s in args.services if s in SERVICES]
    piggies = [PIGGY_BACK_SERVICES[s] for s in args.services if s in PIGGY_BACK_SERVICES]
    cost = CostArgument(args.cost_table) if args.cost_table else None
    piggy_back_prefix = args.piggy_back_prefix
    run(
        client,
        services,
        piggies,
        serializer=gcp_serializer,
        cost=cost,
        piggy_back_prefix=piggy_back_prefix,
    )
    return 0


def main() -> int:
    """Main entry point to be used"""
    return special_agent_main(parse_arguments, agent_gcp_main)
