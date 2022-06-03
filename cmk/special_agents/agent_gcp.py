#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import time
from dataclasses import dataclass, field
from functools import cache
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence, Union

from google.cloud import asset_v1, monitoring_v3
from google.cloud.monitoring_v3 import Aggregation as gAggregation
from google.cloud.monitoring_v3.types import TimeSeries

# Those are enum classes defined in the Aggregation class. Not nice but works
Aligner = gAggregation.Aligner
Reducer = gAggregation.Reducer

from cmk.special_agents.utils.agent_common import (
    ConditionalPiggybackSection,
    SectionWriter,
    special_agent_main,
)
from cmk.special_agents.utils.argument_parsing import Args, create_default_argument_parser

####################
# Type Definitions #
####################


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


@dataclass(unsafe_hash=True)
class Client:
    account_info: dict[str, str] = field(compare=False)
    project: str

    @cache
    def monitoring(self):
        return monitoring_v3.MetricServiceClient.from_service_account_info(self.account_info)

    @cache
    def asset(self):
        return asset_v1.AssetServiceClient.from_service_account_info(self.account_info)


@dataclass(frozen=True)
class Aggregation:
    # Those are of from the enum Aligner and Reducer. MyPy cannot handle those imports
    per_series_aligner: int
    cross_series_reducer: int = Reducer.REDUCE_SUM
    alignment_period: int = 60
    group_by_fields: Sequence[str] = field(default_factory=list)

    def to_obj(self, default_groupby: str) -> monitoring_v3.Aggregation:
        groupbyfields = [default_groupby]
        groupbyfields.extend(self.group_by_fields)
        return monitoring_v3.Aggregation(
            {
                "alignment_period": {"seconds": self.alignment_period},
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
    metrics: list[Metric]
    name: str
    default_groupby: str


# todo: Do I want to have a class that automatically prepends gcp?
Labels = Mapping[str, str]


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
        labeler: Callable[[Asset], Labels],
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

    @staticmethod
    def serialize(obj) -> str:
        return json.dumps(TimeSeries.to_dict(obj.ts))

    @classmethod
    def deserialize(cls, data: str) -> "Result":
        ts = TimeSeries.from_json(data)
        return cls(ts=ts)


@dataclass(frozen=True)
class AssetSection:
    name: str
    assets: Sequence[Asset]
    project: str


@dataclass(frozen=True)
class ResultSection:
    name: str
    results: Iterable[Result]


@dataclass(frozen=True)
class PiggyBackSection:
    name: str
    service_name: str
    labels: Labels
    sections: Iterable[ResultSection]


Section = Union[AssetSection, ResultSection, PiggyBackSection]

#################
# Serialization #
#################


def _asset_serializer(section: AssetSection):
    with SectionWriter("gcp_assets") as w:
        w.append(json.dumps(dict(project=section.project)))
        for a in section.assets:
            w.append(Asset.serialize(a))


def _result_serializer(section: ResultSection):
    with SectionWriter(f"gcp_service_{section.name}") as w:
        for r in section.results:
            w.append(Result.serialize(r))


def _piggyback_serializer(section: PiggyBackSection):
    with ConditionalPiggybackSection(section.name):
        with SectionWriter("labels") as w:
            w.append(json.dumps(section.labels))
        for s in section.sections:
            new_s = ResultSection(f"{section.service_name}_{s.name}", s.results)
            _result_serializer(new_s)


def gcp_serializer(sections: Iterable[Section]) -> None:
    for section in sections:
        if isinstance(section, AssetSection):
            _asset_serializer(section)
        elif isinstance(section, ResultSection):
            _result_serializer(section)
        elif isinstance(section, PiggyBackSection):
            _piggyback_serializer(section)
        else:
            raise NotImplementedError


###########
# Metrics #
###########


@dataclass(frozen=True)
class ResourceFilter:
    label: str
    value: str


def time_series(
    client: Client, service: Service, filter_by: Optional[ResourceFilter]
) -> Iterable[Result]:
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
        request = metric.request(interval, groupby=service.default_groupby, project=client.project)
        try:
            results = client.monitoring().list_time_series(request=request)
        except Exception as e:
            raise RuntimeError(metric.name) from e
        for ts in results:
            result = Result(ts=ts)
            if filter_by is None:
                yield result
            elif ts.resource.labels[filter_by.label] == filter_by.value:
                yield result


def run_metrics(
    client: Client, services: Iterable[Service], filter_by: Optional[ResourceFilter] = None
) -> Iterable[ResultSection]:
    for s in services:
        yield ResultSection(s.name, time_series(client, s, filter_by))


################################
# Asset Information collection #
################################


def gather_assets(client: Client) -> Sequence[Asset]:
    request = asset_v1.ListAssetsRequest(
        parent=f"projects/{client.project}", content_type=asset_v1.ContentType.RESOURCE
    )
    all_assets = client.asset().list_assets(request)
    return [Asset(a) for a in all_assets]


def run_assets(client: Client) -> AssetSection:
    return AssetSection("asset", gather_assets(client), client.project)


##############
# piggy back #
##############


def piggy_back(
    client: Client, service: PiggyBackService, assets: Sequence[Asset]
) -> Iterable[PiggyBackSection]:
    for host in [a for a in assets if a.asset.asset_type == service.asset_type]:
        label = host.asset.resource.data[service.asset_label]
        name = host.asset.resource.data[service.name_label]
        filter_by = ResourceFilter(label=service.metric_label, value=label)
        sections = run_metrics(client, services=service.services, filter_by=filter_by)
        yield PiggyBackSection(
            name=name,
            service_name=service.name,
            labels=service.labeler(host) | {"gcp/project": client.project},
            sections=sections,
        )


def run_piggy_back(
    client: Client, services: Sequence[PiggyBackService], assets: Sequence[Asset]
) -> Iterable[PiggyBackSection]:
    for s in services:
        yield from piggy_back(client, s, assets)


#################
# Orchestration #
#################


def run(
    client: Client,
    services: Sequence[Service],
    piggy_back_services: Sequence[PiggyBackService],
    serializer: Callable[[Union[Iterable[Section], Iterable[PiggyBackSection]]], None],
) -> None:
    assets = run_assets(client)
    serializer([assets])
    serializer(run_metrics(client, services))
    serializer(run_piggy_back(client, piggy_back_services, assets.assets))


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
            name="run.googleapis.com/container/cpu/allocation_time",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MAX,
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
                per_series_aligner=Aligner.ALIGN_PERCENTILE_99,
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
            name="redis.googleapis.com/stats/cache_hit_ratio",
            aggregation=Aggregation(
                per_series_aligner=Aligner.ALIGN_MAX,
            ),
        ),
    ],
)


def default_labeler(asset: Asset) -> Labels:
    if "labels" in asset.asset.resource.data:
        return {f"gcp/labels/{k}": v for k, v in asset.asset.resource.data["labels"].items()}
    return {}


GCE = PiggyBackService(
    name="gce",
    asset_type="compute.googleapis.com/Instance",
    asset_label="id",
    metric_label="instance_id",
    name_label="name",
    labeler=default_labeler,
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

SERVICES = {s.name: s for s in [GCS, FUNCTIONS, RUN, CLOUDSQL, FILESTORE, REDIS]}
PIGGY_BACK_SERVICES = {s.name: s for s in [GCE]}


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
        choices=list(SERVICES) + list(PIGGY_BACK_SERVICES),
        required=True,
    )
    return parser.parse_args(argv)


def agent_gcp_main(args: Args) -> None:
    client = Client(json.loads(args.credentials), args.project)
    services = [SERVICES[s] for s in args.services if s in SERVICES]
    piggies = [PIGGY_BACK_SERVICES[s] for s in args.services if s in PIGGY_BACK_SERVICES]
    run(client, services, piggies, serializer=gcp_serializer)


def main() -> None:
    """Main entry point to be used"""
    special_agent_main(parse_arguments, agent_gcp_main)
