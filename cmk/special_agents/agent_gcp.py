#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import base64
import json
import time
from dataclasses import dataclass, field
from functools import cache
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence

from google.cloud import functions, monitoring_v3, storage  # type: ignore
from google.cloud.monitoring_v3 import Aggregation
from google.cloud.monitoring_v3.types import TimeSeries

# Those are enum classes defined in the Aggregation class. Not nice but works
Aligner = Aggregation.Aligner
Reducer = Aggregation.Reducer

from cmk.special_agents.utils.agent_common import SectionWriter, special_agent_main
from cmk.special_agents.utils.argument_parsing import Args, create_default_argument_parser


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
    def serialize(obj):
        b = TimeSeries.serialize(obj.ts)
        return base64.b64encode(b).decode("utf-8")

    @classmethod
    def deserialize(cls, data: str):
        b = base64.b64decode(data.encode("utf-8"))
        ts = TimeSeries.deserialize(b)
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
        # TODO: actually filter by service filter/labels
        filter_rule = f'metric.type = "{metric.name}"'

        request = {
            "name": f"projects/{client.project}",
            "filter": filter_rule,
            "interval": interval,
            "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
            "aggregation": monitoring_v3.Aggregation(metric.aggregation),
        }
        results = client.monitoring().list_time_series(request=request)
        for ts in results:
            yield Result(ts=ts)


def serialize_items(items: Iterable[Item]) -> str:
    return json.dumps([i.to_dict() for i in items])


def run(client: Client, s: GCPService) -> None:
    with SectionWriter(f"gcp_service_{s.name.lower()}") as w:
        items = s.discover(client)
        w.append(serialize_items(items))
        for result in time_series(client, s):
            w.append(Result.serialize(result))


def parse_arguments(argv: Optional[Sequence[str]]) -> Args:
    parser = create_default_argument_parser(description=__doc__)
    parser.add_argument("--project", type=str, help="Global ID of Project")
    parser.add_argument("--credentials", type=str, help="JSON credentials for service account")
    return parser.parse_args(argv)


def agent_gcp_main(args: Args) -> None:
    client = Client(json.loads(args.credentials), args.project)
    run(client, GCS)
    run(client, FUNCTIONS)


def main() -> None:
    """Main entry point to be used"""
    special_agent_main(parse_arguments, agent_gcp_main)


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
