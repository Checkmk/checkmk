#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs
from collections.abc import Mapping
from typing import Any

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    register,
    render,
    Result,
    Service,
    ServiceLabel,
    State,
)
from cmk.base.plugins.agent_based.utils import gcp

from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


def parse(string_table: StringTable) -> gcp.Section:
    return gcp.parse_gcp(
        string_table, gcp.ResourceKey("database_id"), extract=lambda x: x.split(":")[-1]
    )


register.agent_section(name="gcp_service_cloud_sql", parse_function=parse)
service_namer = gcp.service_name_factory("Cloud SQL")
ASSET_TYPE = gcp.AssetType("sqladmin.googleapis.com/Instance")


def _get_service_labels(
    project: gcp.Project, service: gcp.GCPAsset, item: str
) -> list[ServiceLabel]:
    data = service.resource_data
    labels = (
        [ServiceLabel(f"gcp/labels/{k}", v) for k, v in data["settings"]["userLabels"].items()]
        if "userLabels" in data["settings"]
        else []
    )
    labels.extend(
        [
            ServiceLabel("gcp/location", service.location),
            ServiceLabel("gcp/cloud_sql/name", item),
            ServiceLabel("gcp/cloud_sql/databaseVersion", data["databaseVersion"]),
            ServiceLabel("gcp/cloud_sql/availability", data["settings"]["availabilityType"]),
            ServiceLabel("gcp/projectId", project),
        ]
    )
    return labels


def discover(
    section_gcp_service_cloud_sql: gcp.Section | None,
    section_gcp_assets: gcp.AssetSection | None,
) -> DiscoveryResult:
    assets = gcp.validate_asset_section(section_gcp_assets, "cloud_sql")
    for item, service in assets[ASSET_TYPE].items():
        labels = _get_service_labels(assets.project, service, item)
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
            "cloudsql.googleapis.com/database/up",
            "Up:",
            lambda x: str(bool(x)),
        ),
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


register.check_plugin(
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
        "UNKOWN_STATE": int(State.CRIT),
    },
)


def check_gcp_sql_memory(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_cloud_sql: gcp.Section | None,
    section_gcp_assets: gcp.AssetSection | None,
) -> CheckResult:
    metrics = {
        # percent render expects numbers range 0 to 100 and not fractions.
        "memory_util": gcp.MetricSpec(
            "cloudsql.googleapis.com/database/memory/utilization",
            "Memory",
            render.percent,
            scale=1e2,
        ),
    }
    yield from gcp.check(
        metrics, item, params, section_gcp_service_cloud_sql, ASSET_TYPE, section_gcp_assets
    )


register.check_plugin(
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
            "cloudsql.googleapis.com/database/cpu/utilization", "CPU", render.percent, scale=1e2
        ),
    }
    yield from gcp.check(
        metrics, item, params, section_gcp_service_cloud_sql, ASSET_TYPE, section_gcp_assets
    )


register.check_plugin(
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
            "cloudsql.googleapis.com/database/network/received_bytes_count",
            "In",
            render.networkbandwidth,
        ),
        "net_data_sent": gcp.MetricSpec(
            "cloudsql.googleapis.com/database/network/sent_bytes_count",
            "Out",
            render.networkbandwidth,
        ),
    }
    yield from gcp.check(
        metrics, item, params, section_gcp_service_cloud_sql, ASSET_TYPE, section_gcp_assets
    )


register.check_plugin(
    name="gcp_sql_network",
    sections=["gcp_service_cloud_sql", "gcp_assets"],
    service_name=service_namer("network"),
    check_ruleset_name="gcp_sql_network",
    discovery_function=discover,
    check_function=check_gcp_sql_network,
    check_default_parameters={"net_data_sent": None, "net_data_recv": None},
)


def check_gcp_sql_disk(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_cloud_sql: gcp.Section | None,
    section_gcp_assets: gcp.AssetSection | None,
) -> CheckResult:
    metrics = {
        "fs_used_percent": gcp.MetricSpec(
            "cloudsql.googleapis.com/database/disk/utilization",
            "Disk utilization",
            render.percent,
            scale=1e2,
        ),
        "disk_write_ios": gcp.MetricSpec(
            "cloudsql.googleapis.com/database/disk/write_ops_count", "Write operations", str
        ),
        "disk_read_ios": gcp.MetricSpec(
            "cloudsql.googleapis.com/database/disk/read_ops_count", "Read operations", str
        ),
    }
    yield from gcp.check(
        metrics, item, params, section_gcp_service_cloud_sql, ASSET_TYPE, section_gcp_assets
    )


register.check_plugin(
    name="gcp_sql_disk",
    sections=["gcp_service_cloud_sql", "gcp_assets"],
    service_name=service_namer("disk"),
    check_ruleset_name="gcp_sql_disk",
    discovery_function=discover,
    check_function=check_gcp_sql_disk,
    check_default_parameters={
        "fs_used_percent": (80.0, 90.0),
        "disk_write_ios": None,
        "disk_read_ios": None,
    },
)


def discovery_summary(section: gcp.AssetSection) -> DiscoveryResult:
    yield from gcp.discovery_summary(section, "cloud_sql")


def check_summary(section: gcp.AssetSection) -> CheckResult:
    yield from gcp.check_summary(ASSET_TYPE, "Server", section)


register.check_plugin(
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

        labels = _get_service_labels(assets.project, service, item)
        yield Service(item=item, labels=labels)


def check_gcp_sql_replication(
    item: str,
    params: Mapping[str, Any],
    section_gcp_service_cloud_sql: gcp.Section | None,
    section_gcp_assets: gcp.AssetSection | None,
) -> CheckResult:
    metrics = {
        "replication_lag": gcp.MetricSpec(
            "cloudsql.googleapis.com/database/replication/replica_lag",
            "Replication lag",
            render.timespan,
        )
    }
    yield from gcp.check(
        metrics, item, params, section_gcp_service_cloud_sql, ASSET_TYPE, section_gcp_assets
    )


register.check_plugin(
    name="gcp_sql_replication",
    sections=["gcp_service_cloud_sql", "gcp_assets"],
    service_name=service_namer("replication"),
    check_ruleset_name="gcp_replication_lag",
    discovery_function=discover_gcp_sql_replication,
    check_function=check_gcp_sql_replication,
    check_default_parameters={"replication_lag": None},
)
