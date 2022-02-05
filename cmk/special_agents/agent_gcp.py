#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import base64
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence

from google.cloud import monitoring_v3
from google.cloud.monitoring_v3 import Aggregation
from google.cloud.monitoring_v3.services.metric_service.pagers import ListTimeSeriesPager
from google.cloud.monitoring_v3.types import TimeSeries

# Those are enum classes defined in the Aggregation class. Not nice but works
Aligner = Aggregation.Aligner
Reducer = Aggregation.Reducer

from cmk.special_agents.utils.agent_common import SectionWriter, special_agent_main
from cmk.special_agents.utils.argument_parsing import Args, create_default_argument_parser


@dataclass()
class Client:
    client: monitoring_v3.MetricServiceClient
    project: str

    @classmethod
    def from_service_account_info(cls, account_info: Dict[str, str], project: str):
        c = monitoring_v3.MetricServiceClient.from_service_account_info(account_info)
        return cls(c, project)

    def list_time_series(self, request: Dict[str, Any]) -> ListTimeSeriesPager:
        request["name"] = f"projects/{self.project}"
        return self.client.list_time_series(request)


@dataclass(frozen=True)
class GCPMetric:
    name: str
    aggregation: Dict[str, Any]


@dataclass(frozen=True)
class GCPService:
    metrics: List[GCPMetric]
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
    nanos = int((now - seconds) * 10 ** 9)
    interval = monitoring_v3.TimeInterval(
        {
            "end_time": {"seconds": seconds, "nanos": nanos},
            "start_time": {"seconds": (seconds - 1200), "nanos": nanos},
        }
    )
    for metric in service.metrics:
        # TODO: actually filter by service filter/labels
        filter_rule = f'metric.type = "{metric.name}"'
        results = client.list_time_series(
            request={
                "filter": filter_rule,
                "interval": interval,
                "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                "aggregation": monitoring_v3.Aggregation(metric.aggregation),
            }
        )
        for ts in results:
            yield Result(ts=ts)


def run(client: Client, s: GCPService) -> None:
    with SectionWriter(f"gcp_service_{s.name.lower()}") as w:
        for result in time_series(client, s):
            w.append(Result.serialize(result))


def parse_arguments(argv: Optional[Sequence[str]]) -> Args:
    parser = create_default_argument_parser(description=__doc__)
    parser.add_argument("--project", type=str, help="Global ID of Project")
    parser.add_argument("--credentials", type=str, help="JSON credentials for service account")
    return parser.parse_args(argv)


def agent_gcp_main(args: Args) -> None:
    client = Client.from_service_account_info(json.loads(args.credentials), args.project)
    run(client, GCS)


def main() -> None:
    """Main entry point to be used"""
    special_agent_main(parse_arguments, agent_gcp_main)


GCS = GCPService(
    name="gcs",
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
