#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import time
from dataclasses import dataclass, field
from functools import cache
from typing import Any, Dict, Iterable, List, Optional, Sequence

from google.cloud import asset_v1, monitoring_v3  # type: ignore
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
    def asset(self):
        return asset_v1.AssetServiceClient.from_service_account_info(self.account_info)


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


def run_metrics(client: Client, services: Iterable[GCPService]) -> None:
    for s in services:
        with SectionWriter(f"gcp_service_{s.name.lower()}") as w:
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
#                                                                     #
# A list of all available metrics can be found here:                  #
# https://cloud.google.com/monitoring/api/metrics_gcp                 #
#######################################################################


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


FUNCTIONS = GCPService(
    name="cloud_functions",
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


RUN = GCPService(
    name="cloud_run",
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

CLOUDSQL = GCPService(
    name="cloud_sql",
    metrics=[
        GCPMetric(
            name="cloudsql.googleapis.com/database/up",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.database_id"],
                "per_series_aligner": Aligner.ALIGN_MAX,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
        GCPMetric(
            name="cloudsql.googleapis.com/database/network/received_bytes_count",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.database_id"],
                "per_series_aligner": Aligner.ALIGN_RATE,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
        GCPMetric(
            name="cloudsql.googleapis.com/database/network/sent_bytes_count",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.database_id"],
                "per_series_aligner": Aligner.ALIGN_RATE,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
        GCPMetric(
            name="cloudsql.googleapis.com/database/memory/utilization",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.database_id"],
                "per_series_aligner": Aligner.ALIGN_MAX,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
        GCPMetric(
            name="cloudsql.googleapis.com/database/cpu/utilization",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.database_id"],
                "per_series_aligner": Aligner.ALIGN_MAX,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
        GCPMetric(
            name="cloudsql.googleapis.com/database/state",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.database_id"],
                "per_series_aligner": Aligner.ALIGN_NEXT_OLDER,
                "cross_series_reducer": Reducer.REDUCE_NONE,
            },
        ),
        GCPMetric(
            name="cloudsql.googleapis.com/database/disk/write_ops_count",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.database_id"],
                "per_series_aligner": Aligner.ALIGN_RATE,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
        GCPMetric(
            name="cloudsql.googleapis.com/database/disk/read_ops_count",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.database_id"],
                "per_series_aligner": Aligner.ALIGN_RATE,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
        GCPMetric(
            name="cloudsql.googleapis.com/database/disk/utilization",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.database_id"],
                "per_series_aligner": Aligner.ALIGN_MAX,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
    ],
)

FILESTORE = GCPService(
    name="filestore",
    metrics=[
        GCPMetric(
            name="file.googleapis.com/nfs/server/used_bytes_percent",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.instance_name"],
                "per_series_aligner": Aligner.ALIGN_MAX,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
        GCPMetric(
            name="file.googleapis.com/nfs/server/write_ops_count",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.instance_name"],
                "per_series_aligner": Aligner.ALIGN_RATE,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
        GCPMetric(
            name="file.googleapis.com/nfs/server/read_ops_count",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.instance_name"],
                "per_series_aligner": Aligner.ALIGN_RATE,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
    ],
)

REDIS = GCPService(
    name="redis",
    metrics=[
        GCPMetric(
            name="redis.googleapis.com/stats/cpu_utilization",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.instance_id"],
                "per_series_aligner": Aligner.ALIGN_MAX,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
        GCPMetric(
            name="redis.googleapis.com/stats/memory/usage_ratio",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.instance_id"],
                "per_series_aligner": Aligner.ALIGN_MAX,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
        GCPMetric(
            name="redis.googleapis.com/stats/memory/system_memory_usage_ratio",
            aggregation={
                "alignment_period": {"seconds": 60},
                "group_by_fields": ["resource.instance_id"],
                "per_series_aligner": Aligner.ALIGN_MAX,
                "cross_series_reducer": Reducer.REDUCE_SUM,
            },
        ),
    ],
)

SERVICES = {s.name: s for s in [GCS, FUNCTIONS, RUN, CLOUDSQL, FILESTORE, REDIS]}


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
