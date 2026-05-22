#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.graylog.lib import deserialize_and_merge_json

Section = dict[str, Any]

# <<<graylog_cluster_stats>>>
# [[u'{"stream_rule_count": 7, "input_count_by_type":
# {"org.graylog.plugins.beats.Beats2Input": 1,
# "org.graylog2.inputs.syslog.tcp.SyslogTCPInput": 2,
# "org.graylog2.inputs.syslog.udp.SyslogUDPInput": 1}, "global_input_count":
# 4, "user_count": 3, "mongo": {"host_info": null, "database_stats":
# {"extent_free_list": null, "num_extents": 0, "db": "graylog",
# "storage_size": 1519616, "avg_obj_size": 323.20581808249113,
# "indexes": 106, "ns_size_mb": null, "index_size": 2899968,
# "objects": 7322, "collections": 47, "file_size": null,
# "data_file_version": null, "data_size": 2366513}, "server_status":
# null, "build_info": {"javascript_engine": "mozjs", "compiler_flags":
# null, "git_version": "9779e3cbf9e9afe86e6b29e22520ffb6766e95d4",
# "version": "4.0.12", "sys_info": "deprecated", "debug": false,
# "loader_flags": null, "version_array": [4, 0, 12, 0], "bits": 64,
# "max_bson_object_size": 16777216, "allocator": "tcmalloc"},
# "servers": ["server1:27019", "server2:27018",
# "server3", "server4:27018",
# "server5:27017", "dotsim-vt-02.dpma.de:27017"]},
# "extractor_count_by_type": {},
# "stream_count": 5, "output_count": 0, "stream_rule_count_by_stream":
# {"000000000000000000000001": 0, "000000000000000000000002": 0,
# "000000000000000000000003": 0, "8d7441564fb89f18c1f353e3": 6,
# "8d7423cb4fb89f18c1f33645": 1}, "extractor_count": 0, "ldap_stats":
# {"active_directory": true, "enabled": true, "role_mapping_count": 1,
# "role_count": 10}, "input_count": 4, "output_count_by_type": {},
# "elasticsearch": {"status": "GREEN", "indices_stats": {"store_size":
# 1148947754, "index_count": 3, "id_cache_size": 0,
# "field_data_size": 636952}, "nodes_stats": {"data_only": -1,
# "master_data": -1, "total": 6, "master_only": -1, "client":
# -1}, "cluster_name": "graylog", "cluster_health":
# {"number_of_nodes": 6, "unassigned_shards": 0, "pending_tasks": 0,
# "timed_out": false, "active_primary_shards": 14,
# "pending_tasks_time_in_queue": [], "initializing_shards": 0,
# "active_shards": 20, "number_of_data_nodes": 6,
# "relocating_shards": 0}, "cluster_version": "6.8.2"},
# "dashboard_count": 0, "alarm_stats": {"alert_count": 0,
# "alarmcallback_count_by_type": {}}}']]


def discover_graylog_cluster_stats(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_graylog_cluster_stats(params: Mapping[str, Any], section: Section) -> CheckResult:
    if not section:
        return

    for key, infotext, m_name in [
        ("input_count", "Number of inputs", "num_input"),
        ("output_count", "Number of outputs", "num_output"),
        ("stream_count", "Number of streams", "streams"),
        ("stream_rule_count", "Number of stream rules", "num_stream_rule"),
        ("extractor_count", "Number of extractors", "num_extractor"),
        ("user_count", "Number of user", "num_user"),
    ]:
        data = section.get(key)
        if data is not None:
            yield from check_levels_v1(
                value=data,
                metric_name=m_name,
                levels_upper=params.get(f"{key}_upper", (None, None)),
                levels_lower=params.get(f"{key}_lower", (None, None)),
                render_func=lambda v: f"{int(v)}",
                label=infotext,
            )


agent_section_graylog_cluster_stats = AgentSection(
    name="graylog_cluster_stats",
    parse_function=deserialize_and_merge_json,
)


check_plugin_graylog_cluster_stats = CheckPlugin(
    name="graylog_cluster_stats",
    service_name="Graylog Cluster Stats",
    discovery_function=discover_graylog_cluster_stats,
    check_function=check_graylog_cluster_stats,
    check_ruleset_name="graylog_cluster_stats",
    check_default_parameters={},
)


def discover_graylog_cluster_stats_elastic(section: Section) -> DiscoveryResult:
    if section.get("elasticsearch") is not None:
        yield Service()


def check_graylog_cluster_stats_elastic(
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    elastic_data = section.get("elasticsearch")
    if elastic_data is None:
        return

    for key, infotext in [
        ("cluster_name", "Name"),
        ("cluster_version", "Version"),
    ]:
        value = elastic_data.get(key)
        if value is not None:
            yield Result(state=State.OK, summary=f"{infotext}: {value.title()}")

    status_data = elastic_data.get("status")
    if status_data:
        yield Result(
            state=State(params.get(status_data.lower(), 3)),
            summary=f"Status: {status_data.title()}",
        )

    health_data = elastic_data.get("cluster_health")
    if health_data:
        for health_section, health_info in [
            ("number_of_nodes", "Nodes"),
            ("number_of_data_nodes", "Data nodes"),
            ("active_shards", "Active shards"),
            ("active_primary_shards", "Active primary shards"),
            ("initializing_shards", "Initializing shards"),
            ("relocating_shards", "Relocating shards"),
            ("unassigned_shards", "Unassigned shards"),
            ("pending_tasks", "Pending tasks"),
        ]:
            health_value = health_data.get(health_section)
            if health_value is None:
                continue

            metric_name = (
                f"number_of_{health_section}"
                if health_section == "pending_tasks"
                else health_section
            )

            yield from check_levels_v1(
                value=health_value,
                metric_name=metric_name,
                levels_upper=params.get(f"{health_section}_upper", (None, None)),
                levels_lower=params.get(f"{health_section}_lower", (None, None)),
                render_func=lambda v: f"{int(v)}",
                label=health_info,
            )

        timedout_data = health_data.get("timed_out")
        if timedout_data is not None:
            yield Result(
                state=State.OK,
                summary=f"Timed out: {'yes' if timedout_data else 'no'}",
            )

    indice_data = elastic_data.get("indices_stats")
    if indice_data:
        for section_name, info, hr_func in [
            ("index_count", "Index count", lambda v: f"{int(v)}"),
            ("store_size", "Store size", render.bytes),
            ("id_cache_size", "ID cache size", render.bytes),
            ("field_data_size", "Field data size", render.bytes),
        ]:
            indice_value = indice_data.get(section_name)
            if indice_value is None:
                continue

            yield from check_levels_v1(
                value=indice_value,
                metric_name=section_name,
                levels_upper=params.get(f"{section_name}_upper", (None, None)),
                levels_lower=params.get(f"{section_name}_lower", (None, None)),
                render_func=hr_func,
                label=info,
            )


check_plugin_graylog_cluster_stats_elastic = CheckPlugin(
    name="graylog_cluster_stats_elastic",
    service_name="Graylog Cluster Elasticsearch Stats",
    sections=["graylog_cluster_stats"],
    discovery_function=discover_graylog_cluster_stats_elastic,
    check_function=check_graylog_cluster_stats_elastic,
    check_ruleset_name="graylog_cluster_stats_elastic",
    check_default_parameters={
        "green": 0,
        "yellow": 1,
        "red": 2,
    },
)


def discover_graylog_cluster_stats_mongodb(section: Section) -> DiscoveryResult:
    if section.get("mongo") is not None:
        yield Service()


def check_graylog_cluster_stats_mongodb(params: Mapping[str, Any], section: Section) -> CheckResult:
    mongo_data = section.get("mongo")
    if mongo_data is None:
        return

    db_data = mongo_data.get("database_stats")
    if db_data:
        db_name = db_data.get("db")
        if db_name:
            yield Result(state=State.OK, summary=f"Name: {db_name.title()}")

        version = mongo_data.get("build_info", {}).get("version")
        if version:
            yield Result(state=State.OK, summary=f"Version: {version}")

        for key, infotext, metric_name, hr_func in [
            ("indexes", "Indices", "index_count", lambda v: f"{int(v)}"),
            (
                "storage_size",
                "Allocated storage",
                "mongodb_collection_storage_size",
                render.bytes,
            ),
            ("index_size", "Total size", "indexes_size", render.bytes),
            (
                "data_size",
                "Total size of uncompressed data",
                "mongodb_collection_size",
                render.bytes,
            ),
            ("file_size", "Total data files size", "file_size", render.bytes),
            ("ns_size_mb", "Total namespace size", "namespace_size", render.bytes),
            ("avg_obj_size", "Average document size", "avg_doc_size", render.bytes),
            ("num_extents", "Number of extents", "num_extents", lambda v: f"{int(v)}"),
            ("collections", "Number of collections", "num_collections", lambda v: f"{int(v)}"),
            ("objects", "Number of objects", "num_objects", lambda v: f"{int(v)}"),
        ]:
            db_value = db_data.get(key)
            if db_value is None:
                continue

            yield from check_levels_v1(
                value=db_value,
                metric_name=metric_name,
                levels_upper=params.get(f"{key}_upper", (None, None)),
                levels_lower=params.get(f"{key}_lower", (None, None)),
                render_func=hr_func,
                label=infotext,
            )


check_plugin_graylog_cluster_stats_mongodb = CheckPlugin(
    name="graylog_cluster_stats_mongodb",
    service_name="Graylog Cluster MongoDB Stats",
    sections=["graylog_cluster_stats"],
    discovery_function=discover_graylog_cluster_stats_mongodb,
    check_function=check_graylog_cluster_stats_mongodb,
    check_ruleset_name="graylog_cluster_stats_mongodb",
    check_default_parameters={},
)
