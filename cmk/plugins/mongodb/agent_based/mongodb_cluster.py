#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<mongodb_chunks>>>
# <json>

import json
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, Any]


def parse_mongodb_cluster(string_table: StringTable) -> Section:
    if string_table:
        parsed: Section = json.loads(str(string_table[0][0]))
        return parsed
    return {}


#   .--database------------------------------------------------------------.


def discover_mongodb_cluster_databases(section: Section) -> DiscoveryResult:
    for name in section.get("databases", {}):
        yield Service(item=str(name))


def check_mongodb_cluster_databases(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    """
    checks:
    if database is partitioned (only output)
    if number of collections is 0
    primary shard for database (only output)
    """
    database = section.get("databases", {}).get(item, {})

    yield Result(
        state=State.OK,
        summary=f"Partitioned: {'true' if database.get('partitioned', False) else 'false'}",
    )

    number_of_collections = len(database.get("collections", []))
    collection_info = f"Collections: {number_of_collections}"
    if number_of_collections > 0:
        yield Result(state=State.OK, summary=collection_info)
    else:
        yield Result(state=State.WARN, summary=collection_info)

    yield Result(state=State.OK, summary=f"Primary: {database.get('primary')}")


agent_section_mongodb_cluster = AgentSection(
    name="mongodb_cluster",
    parse_function=parse_mongodb_cluster,
)


check_plugin_mongodb_cluster = CheckPlugin(
    name="mongodb_cluster",
    service_name="MongoDB Database: %s",
    discovery_function=discover_mongodb_cluster_databases,
    check_function=check_mongodb_cluster_databases,
    check_ruleset_name="mongodb_cluster",
    check_default_parameters={},
)


#   .--shards--------------------------------------------------------------.


# description: [([interval for total number of chunks[, number of chunks threshold),...]
BALANCE_THRESHOLDS = [((0, 20), 2), ((21, 79), 4), ((80, 2**31 - 1), 8)]


def discover_mongodb_cluster_shards(section: Section) -> DiscoveryResult:
    for db_name, db_data in section.get("databases", {}).items():
        for coll_name in db_data.get("collections", []):
            yield Service(item=f"{db_name}.{coll_name}")


def check_mongodb_cluster_shards(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    """
    checks:
    if collection is sharded (only output)
    if collection is balanced
    if collection's balancer is disabled
    if shards contain jumbo chunks
    """
    if "databases" not in section:
        return

    database_name, collection_name = _mongodb_cluster_split_namespace(item)

    collection_dict = (
        section.get("databases", {})
        .get(database_name, {})
        .get("collstats", {})
        .get(collection_name, {})
    )

    is_sharded = collection_dict.get("sharded", False)
    yield Result(
        state=State.OK,
        summary=f"Collection: {'sharded' if is_sharded else 'unsharded'}",
    )

    if is_sharded:
        state, summary = _mongodb_cluster_collection_is_balanced(collection_dict)
        yield Result(state=state, summary=summary)

        state, summary = _mongodb_cluster_is_balancer_disabled(collection_dict)
        yield Result(state=state, summary=summary)

        state, summary = _mongodb_cluster_shard_has_jumbos(
            params.get("levels_number_jumbo"), collection_dict
        )
        yield Result(state=state, summary=summary)

    primary_shard_name = (
        section.get("databases", {}).get(database_name, {}).get("primary", "unknown")
    )
    settings_dict = section.get("settings", {})
    shards_dict = section.get("shards", {})

    long_output, perf_data = _generate_mongodb_cluster_long_output(
        is_sharded, collection_dict, primary_shard_name, settings_dict, shards_dict, params
    )
    yield Result(state=State.OK, notice=long_output)
    yield from perf_data


def _mongodb_cluster_is_balancer_disabled(
    collection_dict: Mapping[str, Any],
) -> tuple[State, str]:
    if "noBalance" in collection_dict and collection_dict.get("noBalance", False):
        return State.WARN, "Balancer: disabled"
    return State.OK, "Balancer: enabled"


def _mongodb_cluster_shard_has_jumbos(
    levels: tuple[int, int] | None, collection_dict: Mapping[str, Any]
) -> tuple[State, str]:
    if levels is None:
        return State.OK, "Jumbo: 0"

    warning_info = []
    warning_level = State.OK
    for shard_name in sorted(collection_dict.get("shards", {})):
        number_of_jumbos = collection_dict["shards"][shard_name].get("numberOfJumbos", 0)
        if number_of_jumbos >= levels[1]:
            warning_level = State.CRIT
        elif number_of_jumbos >= levels[0] and warning_level == State.OK:
            warning_level = State.WARN

        if number_of_jumbos >= levels[0]:
            chunks_word = "chunks" if number_of_jumbos > 1 else "chunk"
            warning_info.append(f"{shard_name} ({number_of_jumbos} jumbo {chunks_word})")

    if warning_level == State.OK:
        return warning_level, "Jumbo: 0"
    return warning_level, f"Jumbo: [{', '.join(warning_info)}]"


def _mongodb_cluster_collection_is_balanced(
    collection_dict: Mapping[str, Any],
) -> tuple[State, str]:
    total_number_of_chunks = collection_dict.get("nchunks", 0)
    total_number_of_shards = len(collection_dict.get("shards", [None]))
    average_chunks_per_shard = total_number_of_chunks / total_number_of_shards

    warning_info = []

    balanced = True
    for shard_name in sorted(collection_dict.get("shards", {})):
        number_of_chunks_in_shard = collection_dict["shards"][shard_name].get("numberOfChunks", 0)

        balanced &= _mongodb_cluster_is_balanced(
            total_number_of_chunks, average_chunks_per_shard, number_of_chunks_in_shard
        )

        warning_info.append(f"{shard_name} ({number_of_chunks_in_shard} chunks)")

    if balanced:
        return State.OK, "Chunks: balanced"
    return State.WARN, f"Chunks: unbalanced [{', '.join(warning_info)}]"


def _mongodb_cluster_is_balanced(
    total_number_of_chunks: int,
    average_chunks_per_shard: float,
    number_of_chunks_in_shard: int,
) -> bool:
    """
    < 20 : deviation more than 2 chunks
    20-79: deviation more than 4 chunks
    >= 80: deviation more than 8 chunks
    """
    diff_chunks = number_of_chunks_in_shard - average_chunks_per_shard

    for threshold in BALANCE_THRESHOLDS:
        if threshold[0][0] >= total_number_of_chunks > threshold[0][1]:
            if diff_chunks > threshold[1]:
                return False
    return True


def _generate_mongodb_cluster_long_output(
    is_sharded: bool,
    collection_dict: Mapping[str, Any],
    primary_shard_name: str,
    settings_dict: Mapping[str, Any],
    shards_dict: Mapping[str, Any],
    params: Mapping[str, Any],
) -> tuple[str, list[Metric]]:
    has_chunks = "nchunks" in collection_dict
    has_shards = "shards" in collection_dict

    total_number_of_chunks = collection_dict.get("nchunks", 0)
    chunk_size = settings_dict.get("chunkSize", 65536)
    collection_shards_dict = collection_dict.get("shards", {})
    total_number_of_documents = collection_dict.get("count", 0)
    total_collection_size = collection_dict.get("size", 0)
    storage_size = collection_dict.get("storageSize", 0)
    balancer_status = (
        "disabled"
        if "noBalance" in collection_dict and collection_dict.get("noBalance", False)
        else "enabled"
    )

    collections_info = ["Collection"]
    if has_shards:
        collections_info.append(f"- Shards: {len(collection_shards_dict)}")
    if has_chunks:
        collections_info.append(
            f"- Chunks: {total_number_of_chunks} (Default chunk size: {render.bytes(chunk_size)})"
        )
    collections_info.append(f"- Docs: {total_number_of_documents}")
    collections_info.append(f"- Size: {render.bytes(total_collection_size)}")
    collections_info.append(f"- Storage: {render.bytes(storage_size)}")
    if is_sharded:
        collections_info.append(f"- Balancer: {balancer_status}")

    shard_info = []
    for shard_name in sorted(collection_dict.get("shards", {})):
        aggregated_shards_dict = dict(collection_dict["shards"][shard_name])
        aggregated_shards_dict["hostname"] = shards_dict.get(shard_name, {}).get("host", "unknown")
        aggregated_shards_dict["name"] = shard_name
        aggregated_shards_dict["is_primary"] = shard_name == primary_shard_name
        shard_info.append(
            "\n"
            + _mongodb_cluster_get_shard_statistic_info(
                is_sharded,
                aggregated_shards_dict,
                total_collection_size,
                total_number_of_documents,
            )
        )

    long_output = "\n" + "\n".join(collections_info) + "\n" + "\n".join(shard_info)
    perf_data = _mongodb_cluster_generate_performance_data(collection_dict, params)
    return long_output, perf_data


def _mongodb_cluster_get_shard_statistic_info(
    is_sharded: bool,
    shard_dict: Mapping[str, Any],
    total_shard_size: int,
    total_number_of_documents: int,
) -> str:
    number_of_chunks = shard_dict.get("numberOfChunks", 0)
    number_of_jumbos = shard_dict.get("numberOfJumbos", 0)
    shard_size = shard_dict.get("size", 0)
    number_of_documents = shard_dict.get("count", 0)
    hostname = shard_dict.get("hostname", "unknown")
    shard_name = shard_dict.get("name", "unknown")
    is_primary = shard_dict.get("is_primary", False)

    est_data_percent = (float(shard_size) / total_shard_size * 100) if total_shard_size > 0 else 0
    est_doc_percent = (
        (float(number_of_documents) / total_number_of_documents * 100)
        if total_number_of_documents > 0
        else 0
    )
    est_chunk_data = (float(shard_size) / number_of_chunks) if number_of_chunks > 0 else 0
    est_chunk_count = (float(number_of_documents) / number_of_chunks) if number_of_chunks > 0 else 0

    shard_name_info = f"{shard_name}{' (primary)' if is_primary else ''}"

    output = [f"Shard {shard_name_info}"]
    output.append(f"- Chunks: {number_of_chunks}")
    output.append(f"- Jumbos: {number_of_jumbos}")
    docs_line = f"- Docs: {number_of_documents}"
    if is_sharded:
        docs_line += f" ({est_doc_percent:1.2f}%)"
    output.append(docs_line)
    if is_sharded:
        output.append(f"--- per chunk: ≈ {est_chunk_count:.0f}")
    size_line = f"- Size: {render.bytes(shard_size)}"
    if is_sharded:
        size_line += f" ({est_data_percent:1.2f}%)"
    output.append(size_line)
    if is_sharded:
        output.append(f"--- per chunk: ≈ {render.bytes(est_chunk_data)}")
    output.append(f"- Host: {hostname}")
    return "\n".join(output)


def _mongodb_cluster_generate_performance_data(
    collection_dict: Mapping[str, Any], params: Mapping[str, Any]
) -> list[Metric]:
    has_chunks = "nchunks" in collection_dict

    number_of_chunks = collection_dict.get("nchunks", 0)
    number_of_documents = collection_dict.get("count", 0)
    collection_size = collection_dict.get("size", 0)
    storage_size = collection_dict.get("storageSize", 0)

    total_number_of_jumbos = 0
    has_shards = collection_dict.get("shards", False)
    if has_shards:
        for shard_name in collection_dict["shards"]:
            total_number_of_jumbos += collection_dict["shards"][shard_name].get("numberOfJumbos", 0)

    perfdata: list[Metric] = []
    perfdata.append(Metric("mongodb_collection_size", collection_size))
    perfdata.append(Metric("mongodb_collection_storage_size", storage_size))
    perfdata.append(Metric("mongodb_document_count", number_of_documents))
    if has_chunks:
        perfdata.append(Metric("mongodb_chunk_count", number_of_chunks))
    if has_shards:
        warn, crit = params.get("levels_number_jumbo", (0, 0))
        perfdata.append(
            Metric("mongodb_jumbo_chunk_count", total_number_of_jumbos, levels=(warn, crit))
        )
    return perfdata


def _mongodb_cluster_split_namespace(namespace: str) -> tuple[str, str]:
    try:
        names = namespace.split(".", 1)
        if len(names) > 1:
            return names[0], names[1]
        if len(names) > 0:
            return names[0], ""
    except (ValueError, AttributeError):
        pass
    raise ValueError(f"error parsing namespace {namespace}")


check_plugin_mongodb_cluster_collections = CheckPlugin(
    name="mongodb_cluster_collections",
    service_name="MongoDB Cluster: %s",
    sections=["mongodb_cluster"],
    discovery_function=discover_mongodb_cluster_shards,
    check_function=check_mongodb_cluster_shards,
    check_ruleset_name="mongodb_cluster",
    check_default_parameters={"levels_number_jumbo": (1, 2)},
)


#   .--balancer------------------------------------------------------------.


def discover_mongodb_cluster_balancer(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_mongodb_cluster_balancer(section: Section) -> CheckResult:
    if "balancer" not in section:
        return

    if section.get("balancer", {}).get("balancer_enabled"):
        yield Result(state=State.OK, summary="Balancer: enabled")
    else:
        yield Result(state=State.CRIT, summary="Balancer: disabled")


check_plugin_mongodb_cluster_balancer = CheckPlugin(
    name="mongodb_cluster_balancer",
    service_name="MongoDB Balancer",
    sections=["mongodb_cluster"],
    discovery_function=discover_mongodb_cluster_balancer,
    check_function=check_mongodb_cluster_balancer,
)
