#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs

import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    render,
    Result,
    Service,
    ServiceLabel,
    State,
    StringTable,
)
from cmk.plugins.gcp.lib import gcp
from cmk.plugins.lib.diskstat import check_diskstat_dict_legacy


def parse(string_table: StringTable) -> gcp.Section:
    return gcp.parse_gcp(
        string_table, gcp.ResourceKey("database_id"), extract=lambda x: x.split(":")[-1]
    )


agent_section_gcp_service_cloud_sql = AgentSection(
    name="gcp_service_cloud_sql", parse_function=parse
)
service_namer = gcp.service_name_factory("Cloud SQL")
ASSET_TYPE = gcp.AssetType("sqladmin.googleapis.com/Instance")


def _get_service_labels(service: gcp.GCPAsset, item: str) -> list[ServiceLabel]:
    data = service.resource_data
    labels = (
        [ServiceLabel(f"cmk/gcp/labels/{k}", v) for k, v in data["settings"]["userLabels"].items()]
        if "userLabels" in data["settings"]
        else []
    )
    labels.extend(
        [
            ServiceLabel("cmk/gcp/location", service.location),
            ServiceLabel("cmk/gcp/cloud_sql/name", item),
            ServiceLabel("cmk/gcp/cloud_sql/databaseVersion", data["databaseVersion"]),
            ServiceLabel("cmk/gcp/cloud_sql/availability", data["settings"]["availabilityType"]),
        ]
    )
    return labels


def discover(
    section_gcp_service_cloud_sql: gcp.Section | None,
    section_gcp_assets: gcp.AssetSection | None,
) -> DiscoveryResult:
    assets = gcp.validate_asset_section(section_gcp_assets, "cloud_sql")
    for item, service in assets[ASSET_TYPE].items():
        labels = _get_service_labels(service, item)
        yield Service(item=item, labels=labels)


##############################################################
# Services                                                   #
# - state: use detailed state information                    #
##############################################################


def check_gcp_sql_status(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_cloud_sql: gcp.Section | None,
    section_gcp_assets: gcp.AssetSection | None,
) -> CheckResult:
    if section_gcp_service_cloud_sql is None or not gcp.item_in_section(
        item, ASSET_TYPE, section_gcp_assets
    ):
        return
    metrics = {
        "up": gcp.MetricSpec(
            gcp.MetricExtractionSpec(metric_type="cloudsql.googleapis.com/database/up"),
            gcp.MetricDisplaySpec(label="Up", render_func=lambda x: str(bool(x))),
        )
    }
    timeseries = section_gcp_service_cloud_sql[item].rows
    yield from gcp.generic_check(metrics, timeseries, {"up": None})

    metric_type = "cloudsql.googleapis.com/database/state"
    if (metric := next((r for r in timeseries if r.metric_type == metric_type), None)) is None:
        yield Result(state=State.UNKNOWN, summary="No data available")
        return
    gcp_state = metric.points[0]["value"]["string_value"]
    state = State(params[gcp_state])
    summary = f"State: {gcp_state}"
    yield Result(state=state, summary=summary)


check_plugin_gcp_sql_status = CheckPlugin(
    name="gcp_sql_status",
    sections=["gcp_service_cloud_sql", "gcp_assets"],
    service_name=service_namer("status"),
    check_ruleset_name="gcp_sql_status",
    discovery_function=discover,
    check_function=check_gcp_sql_status,
    check_default_parameters={
        "RUNNING": int(State.OK),
        "SUSPEND": int(State.WARN),
        "RUNNABLE": int(State.OK),
        "PENDING_CREATE": int(State.UNKNOWN),
        "MAINTENANCE": int(State.UNKNOWN),
        "FAILED": int(State.CRIT),
        "UNKNOWN_STATE": int(State.CRIT),
    },
)


def check_gcp_sql_memory(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_cloud_sql: gcp.Section | None,
    section_gcp_assets: gcp.AssetSection | None,
) -> CheckResult:
    metrics = {
        "memory_util": gcp.MetricSpec(
            gcp.MetricExtractionSpec(
                metric_type="cloudsql.googleapis.com/database/memory/utilization",
                scale=1e2,  # percent render expects numbers range 0 to 100 and not fractions.
            ),
            gcp.MetricDisplaySpec(label="Memory", render_func=render.percent),
        )
    }
    yield from gcp.check(
        metrics, item, params, section_gcp_service_cloud_sql, ASSET_TYPE, section_gcp_assets
    )


check_plugin_gcp_sql_memory = CheckPlugin(
    name="gcp_sql_memory",
    sections=["gcp_service_cloud_sql", "gcp_assets"],
    service_name=service_namer("memory"),
    check_ruleset_name="gcp_sql_memory",
    discovery_function=discover,
    check_function=check_gcp_sql_memory,
    check_default_parameters={"memory_util": (80.0, 90.0)},
)


def check_gcp_sql_cpu(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_cloud_sql: gcp.Section | None,
    section_gcp_assets: gcp.AssetSection | None,
) -> CheckResult:
    metrics = {
        "util": gcp.MetricSpec(
            gcp.MetricExtractionSpec(
                metric_type="cloudsql.googleapis.com/database/cpu/utilization", scale=1e2
            ),
            gcp.MetricDisplaySpec(label="CPU", render_func=render.percent),
        )
    }
    yield from gcp.check(
        metrics, item, params, section_gcp_service_cloud_sql, ASSET_TYPE, section_gcp_assets
    )


check_plugin_gcp_sql_cpu = CheckPlugin(
    name="gcp_sql_cpu",
    sections=["gcp_service_cloud_sql", "gcp_assets"],
    service_name=service_namer("CPU"),
    check_ruleset_name="gcp_sql_cpu",
    discovery_function=discover,
    check_function=check_gcp_sql_cpu,
    check_default_parameters={"util": (80.0, 90.0)},
)


def check_gcp_sql_network(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_cloud_sql: gcp.Section | None,
    section_gcp_assets: gcp.AssetSection | None,
) -> CheckResult:
    metrics = {
        "net_data_recv": gcp.MetricSpec(
            gcp.MetricExtractionSpec(
                metric_type="cloudsql.googleapis.com/database/network/received_bytes_count"
            ),
            gcp.MetricDisplaySpec(label="In", render_func=render.networkbandwidth),
        ),
        "net_data_sent": gcp.MetricSpec(
            gcp.MetricExtractionSpec(
                "cloudsql.googleapis.com/database/network/sent_bytes_count",
            ),
            gcp.MetricDisplaySpec(label="Out", render_func=render.networkbandwidth),
        ),
        "connections": gcp.MetricSpec(
            gcp.MetricExtractionSpec(
                "cloudsql.googleapis.com/database/network/connections",
            ),
            gcp.MetricDisplaySpec(label="Active connections", render_func=str),
        ),
    }
    yield from gcp.check(
        metrics, item, params, section_gcp_service_cloud_sql, ASSET_TYPE, section_gcp_assets
    )


check_plugin_gcp_sql_network = CheckPlugin(
    name="gcp_sql_network",
    sections=["gcp_service_cloud_sql", "gcp_assets"],
    service_name=service_namer("network"),
    check_ruleset_name="gcp_sql_network",
    discovery_function=discover,
    check_function=check_gcp_sql_network,
    check_default_parameters={"net_data_sent": None, "net_data_recv": None, "connections": None},
)


def check_gcp_sql_disk(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_cloud_sql: gcp.Section | None,
    section_gcp_assets: gcp.AssetSection | None,
) -> CheckResult:
    if section_gcp_service_cloud_sql is None or not gcp.item_in_section(
        item, ASSET_TYPE, section_gcp_assets
    ):
        return

    metrics = {
        "utilization": gcp.MetricExtractionSpec(
            "cloudsql.googleapis.com/database/disk/utilization"
        ),
        "read_ios": gcp.MetricExtractionSpec(
            "cloudsql.googleapis.com/database/disk/read_ops_count"
        ),
        "write_ios": gcp.MetricExtractionSpec(
            "cloudsql.googleapis.com/database/disk/write_ops_count",
        ),
        "capacity": gcp.MetricExtractionSpec(
            "cloudsql.googleapis.com/database/disk/quota",
        ),
        "used_capacity": gcp.MetricExtractionSpec(
            "cloudsql.googleapis.com/database/disk/bytes_used",
        ),
    }

    timeseries = section_gcp_service_cloud_sql.get(item, gcp.SectionItem(rows=[])).rows

    disk_data = {
        metric_name: gcp.get_value(timeseries, metric_spec)
        for metric_name, metric_spec in metrics.items()
    }

    yield from check_diskstat_dict_legacy(
        params=params,
        disk=disk_data,
        value_store=get_value_store(),
        this_time=time.time(),
    )


check_plugin_gcp_sql_disk = CheckPlugin(
    name="gcp_sql_disk",
    sections=["gcp_service_cloud_sql", "gcp_assets"],
    service_name=service_namer("disk"),
    check_ruleset_name="gcp_sql_disk",
    discovery_function=discover,
    check_function=check_gcp_sql_disk,
    check_default_parameters={
        "disk_utilization": (80.0, 90.0),
        "disk_write_ios": None,
        "disk_read_ios": None,
    },
)


def discovery_summary(section: gcp.AssetSection) -> DiscoveryResult:
    yield from gcp.discovery_summary(section, "cloud_sql")


def check_summary(section: gcp.AssetSection) -> CheckResult:
    yield from gcp.check_summary(ASSET_TYPE, "Server", section)


check_plugin_gcp_sql_summary = CheckPlugin(
    name="gcp_sql_summary",
    sections=["gcp_assets"],
    service_name=service_namer.summary_name(),
    discovery_function=discovery_summary,
    check_function=check_summary,
)


def _has_metric(
    section_gcp_service_cloud_sql: gcp.Section | None, item: str, metric_type: str
) -> bool:
    if not section_gcp_service_cloud_sql:
        return False

    section_item = section_gcp_service_cloud_sql.get(item, gcp.SectionItem(rows=[]))
    return any(row.metric_type == metric_type for row in section_item.rows)


# Custom discovery function since only the follower database has a replica_lag
# metric. The standard discovery would create a service for the leader database
# as well where the nonexistent lag would be shown with default value.
def discover_gcp_sql_replication(
    section_gcp_service_cloud_sql: gcp.Section | None,
    section_gcp_assets: gcp.AssetSection | None,
) -> DiscoveryResult:
    assets = gcp.validate_asset_section(section_gcp_assets, "cloud_sql")

    for item, service in assets[ASSET_TYPE].items():
        if not _has_metric(
            section_gcp_service_cloud_sql,
            item,
            "cloudsql.googleapis.com/database/replication/replica_lag",
        ):
            continue

        labels = _get_service_labels(service, item)
        yield Service(item=item, labels=labels)


def check_gcp_sql_replication(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_cloud_sql: gcp.Section | None,
    section_gcp_assets: gcp.AssetSection | None,
) -> CheckResult:
    metrics = {
        "replication_lag": gcp.MetricSpec(
            gcp.MetricExtractionSpec(
                metric_type="cloudsql.googleapis.com/database/replication/replica_lag"
            ),
            gcp.MetricDisplaySpec(label="Replication lag", render_func=render.timespan),
        )
    }
    yield from gcp.check(
        metrics, item, params, section_gcp_service_cloud_sql, ASSET_TYPE, section_gcp_assets
    )


check_plugin_gcp_sql_replication = CheckPlugin(
    name="gcp_sql_replication",
    sections=["gcp_service_cloud_sql", "gcp_assets"],
    service_name=service_namer("replication"),
    check_ruleset_name="gcp_replication_lag",
    discovery_function=discover_gcp_sql_replication,
    check_function=check_gcp_sql_replication,
    check_default_parameters={"replication_lag": None},
)
