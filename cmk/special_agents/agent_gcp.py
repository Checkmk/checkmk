#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import time
from dataclasses import dataclass, field
from functools import cache
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence

from google.cloud import asset_v1, functions, monitoring_v3, storage  # type: ignore
from google.cloud.monitoring_v3 import Aggregation
from google.cloud.monitoring_v3.types import TimeSeries
from google.oauth2 import service_account  # type: ignore
from googleapiclient.discovery import build, Resource  # type: ignore

# Those are enum classes defined in the Aggregation class. Not nice but works
Aligner = Aggregation.Aligner
Reducer = Aggregation.Reducer

from cmk.special_agents.utils.agent_common import SectionWriter, special_agent_main
from cmk.special_agents.utils.argument_parsing import Args, create_default_argument_parser


@dataclass(frozen=True)
class CloudRunClient:
    credentials: service_account.Credentials
    service: Resource

    @classmethod
    def from_service_account_info(cls, account_info: Dict[str, str]) -> "CloudRunClient":
        credentials = service_account.Credentials.from_service_account_info(account_info)
        scopes = ["https://www.googleapis.com/auth/cloud-platform"]
        scoped_credentials = credentials.with_scopes(list(scopes))
        service = build("run", "v1", credentials=scoped_credentials)
        return cls(scoped_credentials, service)

    def list_services(self, parent: str) -> Mapping[str, Any]:
        request = self.service.namespaces().services().list(parent=parent)
        return request.execute()


@dataclass(unsafe_hash=True)
class Client:
    account_info: Dict[str, str] = field(compare=False)
    project: str

    @cache
    def monitoring(self):
        return monitoring_v3.MetricServiceClient.from_service_account_info(self.account_info)

    @cache
    def storage(self):
        return storage.Client.from_service_account_info(self.account_info)

    @cache
    def functions(self):
        return functions.CloudFunctionsServiceClient.from_service_account_info(self.account_info)

    @cache
    def run(self) -> CloudRunClient:
        return CloudRunClient.from_service_account_info(self.account_info)

    @cache
    def asset(self):
        return asset_v1.AssetServiceClient.from_service_account_info(self.account_info)


@dataclass(frozen=True)
class GCPMetric:
    name: str
    aggregation: Dict[str, Any]


@dataclass(frozen=True)
class Item:
    name: str

    def to_dict(self) -> Mapping[str, str]:
        return {"name": self.name}


# Do not freeze this dataclass to work around a mypy bug. Just pretend it's frozen
# https://github.com/python/mypy/issues/5485#issuecomment-888953325
@dataclass
class GCPService:
    metrics: List[GCPMetric]
    discover: Callable[[Client], Iterable[Item]]
    name: str


@dataclass(frozen=True)
class Result:
    ts: TimeSeries

    @staticmethod
    def serialize(obj) -> str:
        return json.dumps(TimeSeries.to_dict(obj.ts))

    @classmethod
    def deserialize(cls, data: str) -> "Result":
        ts = TimeSeries.from_json(data)
        return cls(ts=ts)


def time_series(client: Client, service: GCPService) -> Iterable[Result]:
    now = time.time()
    seconds = int(now)
    nanos = int((now - seconds) * 10**9)
    interval = monitoring_v3.TimeInterval(
        {
            "end_time": {"seconds": seconds, "nanos": nanos},
            "start_time": {"seconds": (seconds - 1200), "nanos": nanos},
        }
    )
    for metric in service.metrics:
        filter_rule = f'metric.type = "{metric.name}"'

        request = {
            "name": f"projects/{client.project}",
            "filter": filter_rule,
            "interval": interval,
            "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
            "aggregation": monitoring_v3.Aggregation(metric.aggregation),
        }
        try:
            results = client.monitoring().list_time_series(request=request)
        except Exception as e:
            raise RuntimeError(metric.name) from e
        for ts in results:
            yield Result(ts=ts)


def serialize_items(items: Iterable[Item]) -> str:
    return json.dumps([i.to_dict() for i in items])


def run_metrics(client: Client, services: Iterable[GCPService]) -> None:
    for s in services:
        with SectionWriter(f"gcp_service_{s.name.lower()}") as w:
            items = s.discover(client)
            w.append(serialize_items(items))
            for result in time_series(client, s):
                w.append(Result.serialize(result))


################################
# Asset Information collection #
################################


@dataclass(frozen=True)
class Asset:
    asset: asset_v1.Asset

    @staticmethod
    def serialize(obj: "Asset") -> str:
        return json.dumps(asset_v1.Asset.to_dict(obj.asset))

    @classmethod
    def deserialize(cls, data: str) -> "Asset":
        asset = asset_v1.Asset.from_json(data)
        return cls(asset=asset)


def gather_assets(client: Client) -> Iterable[Asset]:
    request = asset_v1.ListAssetsRequest(
        parent=f"projects/{client.project}", content_type=asset_v1.ContentType.RESOURCE
    )
    all_assets = client.asset().list_assets(request)
    for asset in all_assets:
        yield Asset(asset)


def run_assets(client: Client) -> None:
    with SectionWriter("gcp_assets") as w:
        w.append(json.dumps(dict(project=client.project)))
        for asset in gather_assets(client):
            w.append(Asset.serialize(asset))


#################
# Orchestration #
#################


def run(client: Client, services: Sequence[GCPService]) -> None:
    run_assets(client)
    run_metrics(client, services)


#######################################################################
# Configuration of which metrics we collect for a service starts here #
#######################################################################


def discover_buckets(client: Client) -> Iterable[Item]:
    buckets = list(client.storage().list_buckets())
    return (Item(name=b.name) for b in buckets)


GCS = GCPService(
    name="gcs",
    discover=discover_buckets,
    metrics=[
        GCPMetric(
            name="storage.googleapis.com/api/request_count",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.bucket_name"],
                "per_series_aligner": Aligner.ALIGN_RATE,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
        GCPMetric(
            name="storage.googleapis.com/network/sent_bytes_count",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.bucket_name"],
                "per_series_aligner": Aligner.ALIGN_RATE,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
        GCPMetric(
            name="storage.googleapis.com/network/received_bytes_count",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.bucket_name"],
                "per_series_aligner": Aligner.ALIGN_RATE,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
        GCPMetric(
            name="storage.googleapis.com/storage/total_bytes",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.bucket_name"],
                "per_series_aligner": Aligner.ALIGN_MEAN,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
        GCPMetric(
            name="storage.googleapis.com/storage/object_count",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.bucket_name"],
                "per_series_aligner": Aligner.ALIGN_MEAN,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
    ],
)


def discover_functions(client: Client) -> Iterable[Item]:
    # https://cloud.google.com/python/docs/reference/cloudfunctions/latest/google.cloud.functions_v1.types.ListFunctionsRequest
    # See docs why - is used as a location wild card
    parent = f"projects/{client.project}/locations/-"
    functions_info = client.functions().list_functions({"parent": parent})
    return (Item(name=f.name.split("/")[-1]) for f in functions_info)


FUNCTIONS = GCPService(
    name="cloud_functions",
    discover=discover_functions,
    metrics=[
        GCPMetric(
            name="cloudfunctions.googleapis.com/function/execution_count",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.function_name"],
                "per_series_aligner": Aligner.ALIGN_RATE,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
        GCPMetric(
            name="cloudfunctions.googleapis.com/function/network_egress",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.function_name"],
                "per_series_aligner": Aligner.ALIGN_RATE,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
        GCPMetric(
            name="cloudfunctions.googleapis.com/function/user_memory_bytes",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.function_name"],
                "per_series_aligner": Aligner.ALIGN_PERCENTILE_99,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
        GCPMetric(
            name="cloudfunctions.googleapis.com/function/instance_count",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.function_name"],
                "per_series_aligner": Aligner.ALIGN_MAX,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
        GCPMetric(
            name="cloudfunctions.googleapis.com/function/execution_times",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.function_name"],
                "per_series_aligner": Aligner.ALIGN_PERCENTILE_99,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
        GCPMetric(
            name="cloudfunctions.googleapis.com/function/active_instances",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.function_name"],
                "per_series_aligner": Aligner.ALIGN_MAX,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
    ],
)


def discover_run_services(client: Client) -> Iterable[Item]:
    # TODO: have to check how to enable this for ANTHOS
    parent = f"namespaces/{client.project}"
    services = client.run().list_services(parent=parent)
    return (Item(name=s["metadata"]["name"]) for s in services["items"])


RUN = GCPService(
    name="cloud_run",
    discover=discover_run_services,
    metrics=[
        GCPMetric(
            name="run.googleapis.com/container/memory/utilizations",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.service_name"],
                "per_series_aligner": Aligner.ALIGN_PERCENTILE_99,
                "cross_series_reducer": Reducer.REDUCE_MAX,
            },
        ),
        GCPMetric(
            name="run.googleapis.com/container/network/received_bytes_count",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.service_name"],
                "per_series_aligner": Aligner.ALIGN_RATE,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
        GCPMetric(
            name="run.googleapis.com/container/network/sent_bytes_count",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.service_name"],
                "per_series_aligner": Aligner.ALIGN_RATE,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
        GCPMetric(
            name="run.googleapis.com/request_count",
            # TODO get by different status codes
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.service_name"],
                "per_series_aligner": Aligner.ALIGN_MAX,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
        GCPMetric(
            name="run.googleapis.com/container/cpu/allocation_time",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.service_name"],
                "per_series_aligner": Aligner.ALIGN_MAX,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
        GCPMetric(
            name="run.googleapis.com/container/billable_instance_time",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.service_name"],
                "per_series_aligner": Aligner.ALIGN_RATE,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
        GCPMetric(
            name="run.googleapis.com/container/instance_count",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.service_name"],
                "per_series_aligner": Aligner.ALIGN_MAX,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
        GCPMetric(
            name="run.googleapis.com/request_latencies",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.service_name"],
                "per_series_aligner": Aligner.ALIGN_PERCENTILE_99,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
    ],
)

SERVICES = {s.name: s for s in [GCS, FUNCTIONS, RUN]}


def parse_arguments(argv: Optional[Sequence[str]]) -> Args:
    parser = create_default_argument_parser(description=__doc__)
    parser.add_argument("--project", type=str, help="Global ID of Project", required=True)
    parser.add_argument(
        "--credentials", type=str, help="JSON credentials for service account", required=True
    )
    parser.add_argument(
        "--services",
        nargs="+",
        action="extend",
        help=f"implemented services: {','.join(list(SERVICES))}",
        choices=list(SERVICES),
        required=True,
    )
    return parser.parse_args(argv)


def agent_gcp_main(args: Args) -> None:
    client = Client(json.loads(args.credentials), args.project)
    services = [SERVICES[s] for s in args.services]
    run(client, services)


def main() -> None:
    """Main entry point to be used"""
    special_agent_main(parse_arguments, agent_gcp_main)
