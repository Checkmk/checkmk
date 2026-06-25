#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable
from dataclasses import dataclass
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.graylog.lib import deserialize_and_merge_json

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


@dataclass(frozen=True)
class ClusterHealth:
    number_of_nodes: int | None
    number_of_data_nodes: int | None
    active_shards: int | None
    active_primary_shards: int | None
    initializing_shards: int | None
    relocating_shards: int | None
    unassigned_shards: int | None
    pending_tasks: int | None
    timed_out: bool | None


@dataclass(frozen=True)
class IndicesStats:
    index_count: int | None
    store_size: int | None
    id_cache_size: int | None
    field_data_size: int | None


@dataclass(frozen=True)
class Elasticsearch:
    cluster_name: str | None
    cluster_version: str | None
    status: str | None
    cluster_health: ClusterHealth | None
    indices_stats: IndicesStats | None


@dataclass(frozen=True)
class DatabaseStats:
    db: str | None
    indexes: int | None
    storage_size: int | None
    index_size: int | None
    data_size: int | None
    file_size: int | None
    ns_size_mb: int | None
    avg_obj_size: float | None
    num_extents: int | None
    collections: int | None
    objects: int | None


@dataclass(frozen=True)
class Mongo:
    version: str | None
    database_stats: DatabaseStats | None


@dataclass(frozen=True)
class Section:
    input_count: int | None
    output_count: int | None
    stream_count: int | None
    stream_rule_count: int | None
    extractor_count: int | None
    user_count: int | None
    elasticsearch: Elasticsearch | None
    mongo: Mongo | None


class ClusterStatsParams(TypedDict):
    input_count_lower: LevelsT[int]
    input_count_upper: LevelsT[int]
    output_count_lower: LevelsT[int]
    output_count_upper: LevelsT[int]
    stream_count_lower: LevelsT[int]
    stream_count_upper: LevelsT[int]
    stream_rule_count_lower: LevelsT[int]
    stream_rule_count_upper: LevelsT[int]
    extractor_count_lower: LevelsT[int]
    extractor_count_upper: LevelsT[int]
    user_count_lower: LevelsT[int]
    user_count_upper: LevelsT[int]


class ClusterStatsElasticParams(TypedDict):
    green: int
    yellow: int
    red: int
    number_of_nodes_lower: LevelsT[int]
    number_of_nodes_upper: LevelsT[int]
    number_of_data_nodes_lower: LevelsT[int]
    number_of_data_nodes_upper: LevelsT[int]
    active_shards_lower: LevelsT[int]
    active_shards_upper: LevelsT[int]
    active_primary_shards_lower: LevelsT[int]
    active_primary_shards_upper: LevelsT[int]
    unassigned_shards_upper: LevelsT[int]
    initializing_shards_upper: LevelsT[int]
    relocating_shards_upper: LevelsT[int]
    index_count_lower: LevelsT[int]
    index_count_upper: LevelsT[int]


class ClusterStatsMongodbParams(TypedDict):
    indexes_lower: LevelsT[int]
    indexes_upper: LevelsT[int]
    storage_size_upper: LevelsT[int]
    index_size_upper: LevelsT[int]
    data_size_upper: LevelsT[int]
    file_size_upper: LevelsT[int]
    ns_size_mb_upper: LevelsT[int]
    avg_obj_size_upper: LevelsT[int]
    num_extents_lower: LevelsT[int]
    num_extents_upper: LevelsT[int]
    collections_lower: LevelsT[int]
    collections_upper: LevelsT[int]
    objects_upper: LevelsT[int]


def _render_count(value: float) -> str:
    return f"{int(value)}"


# value, metric_name, label, render_func, upper levels, lower levels
_MetricRow = tuple[
    float | None,
    str,
    str,
    Callable[[float], str],
    LevelsT[int] | None,
    LevelsT[int] | None,
]


def _parse_cluster_health(value: object) -> ClusterHealth | None:
    match value:
        case {
            "number_of_nodes": int() | None as number_of_nodes,
            "number_of_data_nodes": int() | None as number_of_data_nodes,
            "active_shards": int() | None as active_shards,
            "active_primary_shards": int() | None as active_primary_shards,
            "initializing_shards": int() | None as initializing_shards,
            "relocating_shards": int() | None as relocating_shards,
            "unassigned_shards": int() | None as unassigned_shards,
            "pending_tasks": int() | None as pending_tasks,
            "timed_out": bool() | None as timed_out,
        }:
            return ClusterHealth(
                number_of_nodes=number_of_nodes,
                number_of_data_nodes=number_of_data_nodes,
                active_shards=active_shards,
                active_primary_shards=active_primary_shards,
                initializing_shards=initializing_shards,
                relocating_shards=relocating_shards,
                unassigned_shards=unassigned_shards,
                pending_tasks=pending_tasks,
                timed_out=timed_out,
            )
        case _:
            return None


def _parse_indices_stats(value: object) -> IndicesStats | None:
    match value:
        case {
            "index_count": int() | None as index_count,
            "store_size": int() | None as store_size,
            "id_cache_size": int() | None as id_cache_size,
            "field_data_size": int() | None as field_data_size,
        }:
            return IndicesStats(
                index_count=index_count,
                store_size=store_size,
                id_cache_size=id_cache_size,
                field_data_size=field_data_size,
            )
        case _:
            return None


def _parse_elasticsearch(value: object) -> Elasticsearch | None:
    match value:
        case {
            "cluster_name": str() | None as cluster_name,
            "status": str() | None as status,
            "cluster_health": cluster_health_raw,
            "indices_stats": indices_stats_raw,
            **rest,
        }:
            match rest.get("cluster_version"):
                case str() | None as cluster_version:
                    pass
                case _:
                    cluster_version = None
            return Elasticsearch(
                cluster_name=cluster_name,
                cluster_version=cluster_version,
                status=status,
                cluster_health=_parse_cluster_health(cluster_health_raw),
                indices_stats=_parse_indices_stats(indices_stats_raw),
            )
        case _:
            return None


def _parse_database_stats(value: object) -> DatabaseStats | None:
    match value:
        case {
            "db": str() | None as db,
            "indexes": int() | None as indexes,
            "storage_size": int() | None as storage_size,
            "index_size": int() | None as index_size,
            "data_size": int() | None as data_size,
            "file_size": int() | None as file_size,
            "ns_size_mb": int() | None as ns_size_mb,
            "avg_obj_size": int() | float() | None as avg_obj_size,
            "num_extents": int() | None as num_extents,
            "collections": int() | None as collections,
            "objects": int() | None as objects,
        }:
            return DatabaseStats(
                db=db,
                indexes=indexes,
                storage_size=storage_size,
                index_size=index_size,
                data_size=data_size,
                file_size=file_size,
                ns_size_mb=ns_size_mb,
                avg_obj_size=avg_obj_size,
                num_extents=num_extents,
                collections=collections,
                objects=objects,
            )
        case _:
            return None


def _parse_mongo(value: object) -> Mongo | None:
    match value:
        case {"database_stats": database_stats_raw, **rest}:
            match rest.get("build_info"):
                case {"version": str() | None as version}:
                    return Mongo(
                        version=version,
                        database_stats=_parse_database_stats(database_stats_raw),
                    )
                case _:
                    return None
        case _:
            return None


def parse_graylog_cluster_stats(string_table: StringTable) -> Section:
    match deserialize_and_merge_json(string_table):
        case {
            "input_count": int() | None as input_count,
            "output_count": int() | None as output_count,
            "stream_count": int() | None as stream_count,
            "stream_rule_count": int() | None as stream_rule_count,
            "extractor_count": int() | None as extractor_count,
            "user_count": int() | None as user_count,
            **rest,
        }:
            return Section(
                input_count=input_count,
                output_count=output_count,
                stream_count=stream_count,
                stream_rule_count=stream_rule_count,
                extractor_count=extractor_count,
                user_count=user_count,
                elasticsearch=_parse_elasticsearch(rest.get("elasticsearch")),
                mongo=_parse_mongo(rest.get("mongo")),
            )
        case _:
            return Section(
                input_count=None,
                output_count=None,
                stream_count=None,
                stream_rule_count=None,
                extractor_count=None,
                user_count=None,
                elasticsearch=None,
                mongo=None,
            )


def discover_graylog_cluster_stats(section: Section) -> DiscoveryResult:
    if any(
        value is not None
        for value in (
            section.input_count,
            section.output_count,
            section.stream_count,
            section.stream_rule_count,
            section.extractor_count,
            section.user_count,
        )
    ):
        yield Service()


def check_graylog_cluster_stats(params: ClusterStatsParams, section: Section) -> CheckResult:
    for value, metric_name, infotext, levels_upper, levels_lower in [
        (
            section.input_count,
            "num_input",
            "Number of inputs",
            params["input_count_upper"],
            params["input_count_lower"],
        ),
        (
            section.output_count,
            "num_output",
            "Number of outputs",
            params["output_count_upper"],
            params["output_count_lower"],
        ),
        (
            section.stream_count,
            "streams",
            "Number of streams",
            params["stream_count_upper"],
            params["stream_count_lower"],
        ),
        (
            section.stream_rule_count,
            "num_stream_rule",
            "Number of stream rules",
            params["stream_rule_count_upper"],
            params["stream_rule_count_lower"],
        ),
        (
            section.extractor_count,
            "num_extractor",
            "Number of extractors",
            params["extractor_count_upper"],
            params["extractor_count_lower"],
        ),
        (
            section.user_count,
            "num_user",
            "Number of user",
            params["user_count_upper"],
            params["user_count_lower"],
        ),
    ]:
        if value is None:
            continue

        yield from check_levels(
            value=value,
            metric_name=metric_name,
            levels_upper=levels_upper,
            levels_lower=levels_lower,
            render_func=_render_count,
            label=infotext,
        )


agent_section_graylog_cluster_stats = AgentSection(
    name="graylog_cluster_stats",
    parse_function=parse_graylog_cluster_stats,
)


check_plugin_graylog_cluster_stats = CheckPlugin(
    name="graylog_cluster_stats",
    service_name="Graylog Cluster Stats",
    discovery_function=discover_graylog_cluster_stats,
    check_function=check_graylog_cluster_stats,
    check_ruleset_name="graylog_cluster_stats",
    check_default_parameters={
        "input_count_lower": ("no_levels", None),
        "input_count_upper": ("no_levels", None),
        "output_count_lower": ("no_levels", None),
        "output_count_upper": ("no_levels", None),
        "stream_count_lower": ("no_levels", None),
        "stream_count_upper": ("no_levels", None),
        "stream_rule_count_lower": ("no_levels", None),
        "stream_rule_count_upper": ("no_levels", None),
        "extractor_count_lower": ("no_levels", None),
        "extractor_count_upper": ("no_levels", None),
        "user_count_lower": ("no_levels", None),
        "user_count_upper": ("no_levels", None),
    },
)


def discover_graylog_cluster_stats_elastic(section: Section) -> DiscoveryResult:
    if section.elasticsearch is not None:
        yield Service()


def check_graylog_cluster_stats_elastic(
    params: ClusterStatsElasticParams,
    section: Section,
) -> CheckResult:
    elastic = section.elasticsearch
    if elastic is None:
        return

    for text_value, infotext in [
        (elastic.cluster_name, "Name"),
        (elastic.cluster_version, "Version"),
    ]:
        if text_value is not None:
            yield Result(state=State.OK, summary=f"{infotext}: {text_value.title()}")

    if elastic.status is not None:
        status_states = {
            "green": params["green"],
            "yellow": params["yellow"],
            "red": params["red"],
        }
        yield Result(
            state=State(status_states.get(elastic.status.lower(), 3)),
            summary=f"Status: {elastic.status.title()}",
        )

    if (health := elastic.cluster_health) is not None:
        for value, metric_name, infotext, levels_upper, levels_lower in [
            (
                health.number_of_nodes,
                "number_of_nodes",
                "Nodes",
                params["number_of_nodes_upper"],
                params["number_of_nodes_lower"],
            ),
            (
                health.number_of_data_nodes,
                "number_of_data_nodes",
                "Data nodes",
                params["number_of_data_nodes_upper"],
                params["number_of_data_nodes_lower"],
            ),
            (
                health.active_shards,
                "active_shards",
                "Active shards",
                params["active_shards_upper"],
                params["active_shards_lower"],
            ),
            (
                health.active_primary_shards,
                "active_primary_shards",
                "Active primary shards",
                params["active_primary_shards_upper"],
                params["active_primary_shards_lower"],
            ),
            (
                health.initializing_shards,
                "initializing_shards",
                "Initializing shards",
                params["initializing_shards_upper"],
                None,
            ),
            (
                health.relocating_shards,
                "relocating_shards",
                "Relocating shards",
                params["relocating_shards_upper"],
                None,
            ),
            (
                health.unassigned_shards,
                "unassigned_shards",
                "Unassigned shards",
                params["unassigned_shards_upper"],
                None,
            ),
            (health.pending_tasks, "number_of_pending_tasks", "Pending tasks", None, None),
        ]:
            if value is None:
                continue

            yield from check_levels(
                value=value,
                metric_name=metric_name,
                levels_upper=levels_upper,
                levels_lower=levels_lower,
                render_func=_render_count,
                label=infotext,
            )

        if health.timed_out is not None:
            yield Result(
                state=State.OK,
                summary=f"Timed out: {'yes' if health.timed_out else 'no'}",
            )

    if (indices := elastic.indices_stats) is not None:
        indices_rows: list[_MetricRow] = [
            (
                indices.index_count,
                "index_count",
                "Index count",
                _render_count,
                params["index_count_upper"],
                params["index_count_lower"],
            ),
            (indices.store_size, "store_size", "Store size", render.bytes, None, None),
            (indices.id_cache_size, "id_cache_size", "ID cache size", render.bytes, None, None),
            (
                indices.field_data_size,
                "field_data_size",
                "Field data size",
                render.bytes,
                None,
                None,
            ),
        ]
        for (
            index_value,
            metric_name,
            infotext,
            render_func,
            levels_upper,
            levels_lower,
        ) in indices_rows:
            if index_value is None:
                continue

            yield from check_levels(
                value=index_value,
                metric_name=metric_name,
                levels_upper=levels_upper,
                levels_lower=levels_lower,
                render_func=render_func,
                label=infotext,
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
        "number_of_nodes_lower": ("no_levels", None),
        "number_of_nodes_upper": ("no_levels", None),
        "number_of_data_nodes_lower": ("no_levels", None),
        "number_of_data_nodes_upper": ("no_levels", None),
        "active_shards_lower": ("no_levels", None),
        "active_shards_upper": ("no_levels", None),
        "active_primary_shards_lower": ("no_levels", None),
        "active_primary_shards_upper": ("no_levels", None),
        "unassigned_shards_upper": ("no_levels", None),
        "initializing_shards_upper": ("no_levels", None),
        "relocating_shards_upper": ("no_levels", None),
        "index_count_lower": ("no_levels", None),
        "index_count_upper": ("no_levels", None),
    },
)


def discover_graylog_cluster_stats_mongodb(section: Section) -> DiscoveryResult:
    if section.mongo is not None:
        yield Service()


def check_graylog_cluster_stats_mongodb(
    params: ClusterStatsMongodbParams, section: Section
) -> CheckResult:
    if section.mongo is None or (db := section.mongo.database_stats) is None:
        return

    if db.db is not None:
        yield Result(state=State.OK, summary=f"Name: {db.db.title()}")

    if section.mongo.version is not None:
        yield Result(state=State.OK, summary=f"Version: {section.mongo.version}")

    mongo_rows: list[_MetricRow] = [
        (
            db.indexes,
            "index_count",
            "Indices",
            _render_count,
            params["indexes_upper"],
            params["indexes_lower"],
        ),
        (
            db.storage_size,
            "mongodb_collection_storage_size",
            "Allocated storage",
            render.bytes,
            params["storage_size_upper"],
            None,
        ),
        (
            db.index_size,
            "indexes_size",
            "Total size",
            render.bytes,
            params["index_size_upper"],
            None,
        ),
        (
            db.data_size,
            "mongodb_collection_size",
            "Total size of uncompressed data",
            render.bytes,
            params["data_size_upper"],
            None,
        ),
        (
            db.file_size,
            "file_size",
            "Total data files size",
            render.bytes,
            params["file_size_upper"],
            None,
        ),
        (
            db.ns_size_mb,
            "namespace_size",
            "Total namespace size",
            render.bytes,
            params["ns_size_mb_upper"],
            None,
        ),
        (
            db.avg_obj_size,
            "avg_doc_size",
            "Average document size",
            render.bytes,
            params["avg_obj_size_upper"],
            None,
        ),
        (
            db.num_extents,
            "num_extents",
            "Number of extents",
            _render_count,
            params["num_extents_upper"],
            params["num_extents_lower"],
        ),
        (
            db.collections,
            "num_collections",
            "Number of collections",
            _render_count,
            params["collections_upper"],
            params["collections_lower"],
        ),
        (
            db.objects,
            "num_objects",
            "Number of objects",
            _render_count,
            params["objects_upper"],
            None,
        ),
    ]
    for value, metric_name, infotext, render_func, levels_upper, levels_lower in mongo_rows:
        if value is None:
            continue

        yield from check_levels(
            value=value,
            metric_name=metric_name,
            levels_upper=levels_upper,
            levels_lower=levels_lower,
            render_func=render_func,
            label=infotext,
        )


check_plugin_graylog_cluster_stats_mongodb = CheckPlugin(
    name="graylog_cluster_stats_mongodb",
    service_name="Graylog Cluster MongoDB Stats",
    sections=["graylog_cluster_stats"],
    discovery_function=discover_graylog_cluster_stats_mongodb,
    check_function=check_graylog_cluster_stats_mongodb,
    check_ruleset_name="graylog_cluster_stats_mongodb",
    check_default_parameters={
        "indexes_lower": ("no_levels", None),
        "indexes_upper": ("no_levels", None),
        "storage_size_upper": ("no_levels", None),
        "index_size_upper": ("no_levels", None),
        "data_size_upper": ("no_levels", None),
        "file_size_upper": ("no_levels", None),
        "ns_size_mb_upper": ("no_levels", None),
        "avg_obj_size_upper": ("no_levels", None),
        "num_extents_lower": ("no_levels", None),
        "num_extents_upper": ("no_levels", None),
        "collections_lower": ("no_levels", None),
        "collections_upper": ("no_levels", None),
        "objects_upper": ("no_levels", None),
    },
)
