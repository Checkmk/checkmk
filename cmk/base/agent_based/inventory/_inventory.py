#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module is the main entry point for the inventory tree creation/deletion of hosts.

CL:
- 'cmk -i[i] ...' is intended to be a kind of preview and does not store any trees.
- 'cmk --inventory-as-check ...' is the related command of the HW/SW Inventory service,
    ie. a tree is created, stored and compared to the old one if it exists,
    if and only if there are NO errors while executing inventory plugins.
"""

from __future__ import annotations

import contextlib
import itertools
import time
from collections.abc import Collection, Container, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.tty as tty
from cmk.utils.log import console, section
from cmk.utils.structured_data import (
    make_filter_from_choice,
    parse_visible_raw_path,
    RawIntervalsFromConfig,
    RetentionIntervals,
    SDPath,
    StructuredDataNode,
    UpdateResult,
)
from cmk.utils.type_defs import (
    HostName,
    HWSWInventoryParameters,
    InventoryPluginName,
    ParsedSectionName,
    SectionName,
)

from cmk.checkers import (
    FetcherFunction,
    HostKey,
    ParserFunction,
    PInventoryPlugin,
    PSectionPlugin,
    SourceType,
    SummarizerFunction,
)
from cmk.checkers.checkresults import ActiveCheckResult
from cmk.checkers.host_sections import HostSections

from cmk.base.agent_based.data_provider import (
    filter_out_errors,
    make_providers,
    Provider,
    ResolvedResult,
    store_piggybacked_sections,
)
from cmk.base.agent_based.utils import check_parsing_errors, get_cache_info, get_section_kwargs
from cmk.base.api.agent_based.inventory_classes import Attributes, TableRow
from cmk.base.config import ConfigCache

__all__ = [
    "inventorize_status_data_of_real_host",
    "check_inventory_tree",
]


@dataclass(frozen=True)
class CheckInventoryTreeResult:
    processing_failed: bool
    no_data_or_files: bool
    check_result: ActiveCheckResult
    inventory_tree: StructuredDataNode
    update_result: UpdateResult


def check_inventory_tree(
    host_name: HostName,
    *,
    config_cache: ConfigCache,
    fetcher: FetcherFunction,
    parser: ParserFunction,
    summarizer: SummarizerFunction,
    inventory_parameters: Callable[[HostName, PInventoryPlugin], dict[str, object]],
    section_plugins: Mapping[SectionName, PSectionPlugin],
    inventory_plugins: Mapping[InventoryPluginName, PInventoryPlugin],
    run_plugin_names: Container[InventoryPluginName],
    parameters: HWSWInventoryParameters,
    old_tree: StructuredDataNode,
) -> CheckInventoryTreeResult:
    if config_cache.is_cluster(host_name):
        inventory_tree = _inventorize_cluster(nodes=config_cache.nodes_of(host_name) or [])
        return CheckInventoryTreeResult(
            processing_failed=False,
            no_data_or_files=False,
            check_result=ActiveCheckResult.from_subresults(
                *_check_trees(
                    parameters=parameters,
                    inventory_tree=inventory_tree,
                    status_data_tree=StructuredDataNode(),
                    old_tree=old_tree,
                ),
            ),
            inventory_tree=inventory_tree,
            update_result=UpdateResult(),
        )

    fetched = fetcher(host_name, ip_address=None)
    host_sections = parser((f[0], f[1]) for f in fetched)
    host_sections_no_error = filter_out_errors(host_sections)
    store_piggybacked_sections(host_sections_no_error)

    providers = make_providers(host_sections_no_error, section_plugins)

    trees, update_result = _inventorize_real_host(
        now=int(time.time()),
        items_of_inventory_plugins=list(
            _collect_inventory_plugin_items(
                host_name,
                inventory_parameters=inventory_parameters,
                providers=providers,
                inventory_plugins=inventory_plugins,
                run_plugin_names=run_plugin_names,
            )
        ),
        raw_intervals_from_config=config_cache.inv_retention_intervals(host_name),
        old_tree=old_tree,
    )

    # The call to `parsing_errors()` must be *after*
    # `_collect_inventory_plugin_items()` because the broker implements
    # an implicit protocol where `parsing_errors()` is empty until other
    # methods of the broker have been called.
    parsing_errors: Sequence[str] = list(
        itertools.chain.from_iterable(resolver.parsing_errors for resolver in providers.values())
    )
    processing_failed = any(
        host_section.is_error() for _source, host_section in host_sections
    ) or bool(parsing_errors)
    no_data_or_files = _no_data_or_files(host_name, host_sections_no_error.values())

    return CheckInventoryTreeResult(
        processing_failed=processing_failed,
        no_data_or_files=no_data_or_files,
        check_result=ActiveCheckResult.from_subresults(
            *itertools.chain(
                _check_fetched_data_or_trees(
                    parameters=parameters,
                    inventory_tree=trees.inventory,
                    status_data_tree=trees.status_data,
                    old_tree=old_tree,
                    processing_failed=processing_failed,
                    no_data_or_files=no_data_or_files,
                ),
                (r for r in summarizer(host_sections) if r.state != 0),
                check_parsing_errors(parsing_errors, error_state=parameters.fail_status),
            )
        ),
        inventory_tree=trees.inventory,
        update_result=update_result,
    )


#   .--cluster inventory---------------------------------------------------.
#   |                         _           _                                |
#   |                     ___| |_   _ ___| |_ ___ _ __                     |
#   |                    / __| | | | / __| __/ _ \ '__|                    |
#   |                   | (__| | |_| \__ \ ||  __/ |                       |
#   |                    \___|_|\__,_|___/\__\___|_|                       |
#   |                                                                      |
#   |             _                      _                                 |
#   |            (_)_ ____   _____ _ __ | |_ ___  _ __ _   _               |
#   |            | | '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |              |
#   |            | | | | \ V /  __/ | | | || (_) | |  | |_| |              |
#   |            |_|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |              |
#   |                                                  |___/               |
#   '----------------------------------------------------------------------'


def _inventorize_cluster(*, nodes: list[HostName]) -> StructuredDataNode:
    inventory_tree = StructuredDataNode()

    _add_cluster_property_to(inventory_tree=inventory_tree, is_cluster=True)

    if nodes:
        node = inventory_tree.setdefault_node(
            ("software", "applications", "check_mk", "cluster", "nodes")
        )
        node.table.add_key_columns(["name"])
        node.table.add_rows([{"name": node_name} for node_name in nodes])

    return inventory_tree


def _no_data_or_files(host_name: HostName, host_sections: Iterable[HostSections]) -> bool:
    if any(host_sections):
        return False

    if Path(cmk.utils.paths.inventory_output_dir, str(host_name)).exists():
        return False

    if Path(cmk.utils.paths.status_data_dir, str(host_name)).exists():
        return False

    if (archive := Path(cmk.utils.paths.inventory_archive_dir, str(host_name))).exists() and any(
        archive.iterdir()
    ):
        return False

    return True


# .
#   .--real host inventory-------------------------------------------------.
#   |                              _   _               _                   |
#   |               _ __ ___  __ _| | | |__   ___  ___| |_                 |
#   |              | '__/ _ \/ _` | | | '_ \ / _ \/ __| __|                |
#   |              | | |  __/ (_| | | | | | | (_) \__ \ |_                 |
#   |              |_|  \___|\__,_|_| |_| |_|\___/|___/\__|                |
#   |                                                                      |
#   |             _                      _                                 |
#   |            (_)_ ____   _____ _ __ | |_ ___  _ __ _   _               |
#   |            | | '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |              |
#   |            | | | | \ V /  __/ | | | || (_) | |  | |_| |              |
#   |            |_|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |              |
#   |                                                  |___/               |
#   '----------------------------------------------------------------------'


#   ---inventorize real host------------------------------------------------


def _inventorize_real_host(
    *,
    now: int,
    items_of_inventory_plugins: Collection[ItemsOfInventoryPlugin],
    raw_intervals_from_config: RawIntervalsFromConfig,
    old_tree: StructuredDataNode,
) -> tuple[InventoryTrees, UpdateResult]:
    section.section_step("Create inventory or status data tree")

    trees = _create_trees_from_inventory_plugin_items(items_of_inventory_plugins)

    section.section_step("May update inventory tree")

    update_result = _may_update(
        now=now,
        items_of_inventory_plugins=items_of_inventory_plugins,
        raw_intervals_from_config=raw_intervals_from_config,
        inventory_tree=trees.inventory,
        previous_tree=old_tree,
    )

    if not trees.inventory.is_empty():
        _add_cluster_property_to(inventory_tree=trees.inventory, is_cluster=False)

    return trees, update_result


#   ---do status data inventory---------------------------------------------


def inventorize_status_data_of_real_host(
    host_name: HostName,
    *,
    inventory_parameters: Callable[[HostName, PInventoryPlugin], dict[str, object]],
    providers: Mapping[HostKey, Provider],
    inventory_plugins: Mapping[InventoryPluginName, PInventoryPlugin],
    run_plugin_names: Container[InventoryPluginName],
) -> StructuredDataNode:
    return _create_trees_from_inventory_plugin_items(
        _collect_inventory_plugin_items(
            host_name,
            inventory_parameters=inventory_parameters,
            providers=providers,
            inventory_plugins=inventory_plugins,
            run_plugin_names=run_plugin_names,
        )
    ).status_data


# .
#   .--inventory plugin items----------------------------------------------.
#   |             _                      _                                 |
#   |            (_)_ ____   _____ _ __ | |_ ___  _ __ _   _               |
#   |            | | '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |              |
#   |            | | | | \ V /  __/ | | | || (_) | |  | |_| |              |
#   |            |_|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |              |
#   |                                                  |___/               |
#   |              _             _         _ _                             |
#   |        _ __ | |_   _  __ _(_)_ __   (_) |_ ___ _ __ ___  ___         |
#   |       | '_ \| | | | |/ _` | | '_ \  | | __/ _ \ '_ ` _ \/ __|        |
#   |       | |_) | | |_| | (_| | | | | | | | ||  __/ | | | | \__ \        |
#   |       | .__/|_|\__,_|\__, |_|_| |_| |_|\__\___|_| |_| |_|___/        |
#   |       |_|            |___/                                           |
#   '----------------------------------------------------------------------'


@dataclass(frozen=True)
class ItemsOfInventoryPlugin:
    items: list[Attributes | TableRow]
    raw_cache_info: tuple[int, int] | None


def _collect_inventory_plugin_items(
    host_name: HostName,
    *,
    inventory_parameters: Callable[[HostName, PInventoryPlugin], dict[str, object]],
    providers: Mapping[HostKey, Provider],
    inventory_plugins: Mapping[InventoryPluginName, PInventoryPlugin],
    run_plugin_names: Container[InventoryPluginName],
) -> Iterator[ItemsOfInventoryPlugin]:
    section.section_step("Executing inventory plugins")

    class_mutex: dict[tuple[str, ...], str] = {}
    for plugin_name, inventory_plugin in inventory_plugins.items():
        if plugin_name not in run_plugin_names:
            continue

        for source_type in (SourceType.HOST, SourceType.MANAGEMENT):
            if not (
                kwargs := get_section_kwargs(
                    providers, HostKey(host_name, source_type), inventory_plugin.sections
                )
            ):
                console.vverbose(
                    f" {tty.yellow}{tty.bold}{plugin_name}{tty.normal}: skipped (no data)\n"
                )
                continue

            # Inventory functions can optionally have a second argument: parameters.
            # These are configured via rule sets (much like check parameters).
            with contextlib.suppress(ValueError):
                kwargs = {
                    **kwargs,
                    "params": inventory_parameters(host_name, inventory_plugin),
                }

            try:
                inventory_plugin_items = [
                    _parse_inventory_plugin_item(
                        item,
                        class_mutex.setdefault(tuple(item.path), item.__class__.__name__),
                    )
                    for item in inventory_plugin.inventory_function(**kwargs)
                ]
            except Exception as exception:
                # TODO(ml): What is the `if cmk.utils.debug.enabled()` actually good for?
                if cmk.utils.debug.enabled():
                    raise

                console.warning(
                    f" {tty.red}{tty.bold}{plugin_name}{tty.normal}: failed: {exception}\n"
                )
                continue

            def __iter(
                section_names: Iterable[ParsedSectionName], providers: Mapping[HostKey, Provider]
            ) -> Iterable[ResolvedResult]:
                for provider in providers.values():
                    yield from (
                        resolved
                        for section_name in section_names
                        if (resolved := provider.resolve(section_name)) is not None
                    )

            yield ItemsOfInventoryPlugin(
                items=inventory_plugin_items,
                raw_cache_info=get_cache_info(
                    tuple(
                        cache_info
                        for resolved in __iter(inventory_plugin.sections, providers)
                        if (cache_info := resolved.cache_info) is not None
                    )
                ),
            )

            console.verbose(f" {tty.green}{tty.bold}{plugin_name}{tty.normal}: ok\n")


def _parse_inventory_plugin_item(item: object, expected_class_name: str) -> Attributes | TableRow:
    if not isinstance(item, (Attributes, TableRow)):
        # can't happen, inventory results are filtered
        raise NotImplementedError()

    if item.__class__.__name__ != expected_class_name:
        raise TypeError(
            f"Cannot create {item.__class__.__name__} at path {item.path}:"
            f" this is a {expected_class_name} node."
        )

    return item


# .
#   .--creating trees------------------------------------------------------.
#   |                       _   _               _                          |
#   |    ___ _ __ ___  __ _| |_(_)_ __   __ _  | |_ _ __ ___  ___  ___     |
#   |   / __| '__/ _ \/ _` | __| | '_ \ / _` | | __| '__/ _ \/ _ \/ __|    |
#   |  | (__| | |  __/ (_| | |_| | | | | (_| | | |_| | |  __/  __/\__ \    |
#   |   \___|_|  \___|\__,_|\__|_|_| |_|\__, |  \__|_|  \___|\___||___/    |
#   |                                   |___/                              |
#   '----------------------------------------------------------------------'


@dataclass(frozen=True)
class InventoryTrees:
    inventory: StructuredDataNode
    status_data: StructuredDataNode


def _create_trees_from_inventory_plugin_items(
    items_of_inventory_plugins: Iterable[ItemsOfInventoryPlugin],
) -> InventoryTrees:
    inventory_tree = StructuredDataNode()
    status_data_tree = StructuredDataNode()

    for items_of_inventory_plugin in items_of_inventory_plugins:
        for item in items_of_inventory_plugin.items:
            if isinstance(item, Attributes):
                if item.inventory_attributes:
                    node = inventory_tree.setdefault_node(tuple(item.path))
                    node.attributes.add_pairs(item.inventory_attributes)

                if item.status_attributes:
                    node = status_data_tree.setdefault_node(tuple(item.path))
                    node.attributes.add_pairs(item.status_attributes)

            elif isinstance(item, TableRow):
                # do this always, it sets key_columns!
                node = inventory_tree.setdefault_node(tuple(item.path))
                node.table.add_key_columns(sorted(item.key_columns))
                node.table.add_rows([{**item.key_columns, **item.inventory_columns}])

                if item.status_columns:
                    node = status_data_tree.setdefault_node(tuple(item.path))
                    node.table.add_key_columns(sorted(item.key_columns))
                    node.table.add_rows([{**item.key_columns, **item.status_columns}])

    return InventoryTrees(
        inventory=inventory_tree,
        status_data=status_data_tree,
    )


# .
#   .--retentions----------------------------------------------------------.
#   |                     _             _   _                              |
#   |            _ __ ___| |_ ___ _ __ | |_(_) ___  _ __  ___              |
#   |           | '__/ _ \ __/ _ \ '_ \| __| |/ _ \| '_ \/ __|             |
#   |           | | |  __/ ||  __/ | | | |_| | (_) | | | \__ \             |
#   |           |_|  \___|\__\___|_| |_|\__|_|\___/|_| |_|___/             |
#   |                                                                      |
#   '----------------------------------------------------------------------'

# Data for the HW/SW Inventory has a validity period (live data or persisted).
# With the retention intervals configuration you can keep specific attributes or table columns
# longer than their validity period.
#
# 1.) Collect cache infos from plugins if and only if there is a configured 'path-to-node' and
#     attributes/table keys entry in the ruleset 'Retention intervals for HW/SW inventory
#     entities'.
#
# 2.) Process collected cache infos - handle the following four cases via AttributesUpdater,
#     TableUpdater:
#
#       previous node | inv node | retention intervals from
#     -----------------------------------------------------------------------------------
#       no            | no       | None
#       no            | yes      | inv_node keys
#       yes           | no       | previous_node keys
#       yes           | yes      | previous_node keys + inv_node keys
#
#     - If there's no previous node then filtered keys + intervals of current node is stored
#       (like a first run) and will be checked against the future node in the next run.
#     - if there's a previous node then check if the data is recent enough and merge
#       attributes/tables data from the previous node with the current one.
#       'Recent enough' means: now <= cache_at + cache_interval + retention_interval
#       where cache_at, cache_interval: from agent data (or set to (now, 0) if not persisted),
#             retention_interval: configured in the above ruleset


def _may_update(
    *,
    now: int,
    items_of_inventory_plugins: Collection[ItemsOfInventoryPlugin],
    raw_intervals_from_config: RawIntervalsFromConfig,
    inventory_tree: StructuredDataNode,
    previous_tree: StructuredDataNode,
) -> UpdateResult:
    if not raw_intervals_from_config:
        return UpdateResult()

    raw_cache_info_by_path_and_type = {
        (tuple(item.path), item.__class__.__name__): items_of_inventory_plugin.raw_cache_info
        for items_of_inventory_plugin in items_of_inventory_plugins
        for item in items_of_inventory_plugin.items
    }

    def _get_raw_cache_info(
        key: tuple[SDPath, Literal["Attributes", "TableRow"]]
    ) -> tuple[int, int]:
        if (raw_cache_info := raw_cache_info_by_path_and_type.get(key)) is None:
            return (now, 0)
        return raw_cache_info

    results = []
    for entry in raw_intervals_from_config:
        node_path = tuple(parse_visible_raw_path(entry["visible_raw_path"]))

        if (previous_node := previous_tree.get_node(node_path)) is None:
            previous_node = StructuredDataNode()

        if (inv_node := inventory_tree.get_node(node_path)) is None:
            inv_node = inventory_tree.setdefault_node(node_path)

        if choices_for_attributes := entry.get("attributes"):
            raw_cache_info = _get_raw_cache_info((node_path, "Attributes"))
            results.append(
                inv_node.attributes.update_from_previous(
                    now,
                    previous_node.attributes,
                    make_filter_from_choice(choices_for_attributes),
                    RetentionIntervals.from_config(
                        cached_at=raw_cache_info[0],
                        cache_interval=raw_cache_info[1],
                        retention_interval=entry["interval"],
                    ),
                )
            )

        elif choices_for_table := entry.get("columns"):
            raw_cache_info = _get_raw_cache_info((node_path, "TableRow"))
            results.append(
                inv_node.table.update_from_previous(
                    now,
                    previous_node.table,
                    make_filter_from_choice(choices_for_table),
                    RetentionIntervals.from_config(
                        cached_at=raw_cache_info[0],
                        cache_interval=raw_cache_info[1],
                        retention_interval=entry["interval"],
                    ),
                )
            )

    return UpdateResult.from_results(results)


# .
#   .--cluster properties--------------------------------------------------.
#   |                         _           _                                |
#   |                     ___| |_   _ ___| |_ ___ _ __                     |
#   |                    / __| | | | / __| __/ _ \ '__|                    |
#   |                   | (__| | |_| \__ \ ||  __/ |                       |
#   |                    \___|_|\__,_|___/\__\___|_|                       |
#   |                                                                      |
#   |                                           _   _                      |
#   |           _ __  _ __ ___  _ __   ___ _ __| |_(_) ___  ___            |
#   |          | '_ \| '__/ _ \| '_ \ / _ \ '__| __| |/ _ \/ __|           |
#   |          | |_) | | | (_) | |_) |  __/ |  | |_| |  __/\__ \           |
#   |          | .__/|_|  \___/| .__/ \___|_|   \__|_|\___||___/           |
#   |          |_|             |_|                                         |
#   '----------------------------------------------------------------------'


def _add_cluster_property_to(*, inventory_tree: StructuredDataNode, is_cluster: bool) -> None:
    node = inventory_tree.setdefault_node(("software", "applications", "check_mk", "cluster"))
    node.attributes.add_pairs({"is_cluster": is_cluster})


# .
#   .--checks--------------------------------------------------------------.
#   |                         _               _                            |
#   |                     ___| |__   ___  ___| | _____                     |
#   |                    / __| '_ \ / _ \/ __| |/ / __|                    |
#   |                   | (__| | | |  __/ (__|   <\__ \                    |
#   |                    \___|_| |_|\___|\___|_|\_\___/                    |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _check_fetched_data_or_trees(
    *,
    parameters: HWSWInventoryParameters,
    inventory_tree: StructuredDataNode,
    status_data_tree: StructuredDataNode,
    old_tree: StructuredDataNode,
    no_data_or_files: bool,
    processing_failed: bool,
) -> Iterator[ActiveCheckResult]:
    if no_data_or_files:
        yield ActiveCheckResult(0, "No data yet, please be patient")
        return

    if processing_failed:
        # Inventory trees in Checkmk <2.2 the cluster property was added in any case.
        # Since Checkmk 2.2 we changed this behaviour: see werk 14836.
        # In order to avoid a lot of "useless" warnings we check the following:
        if (
            inventory_tree.count_entries() == 1
            and (
                cluster_attributes := inventory_tree.get_attributes(
                    ("software", "applications", "check_mk", "cluster")
                )
            )
            is not None
            and cluster_attributes.pairs.get("is_cluster") in [True, False]
        ):
            yield ActiveCheckResult(0, "No further data for tree update")
        else:
            yield ActiveCheckResult(
                parameters.fail_status,
                "Did not update the tree due to at least one error",
            )

    yield from _check_trees(
        parameters=parameters,
        inventory_tree=inventory_tree,
        status_data_tree=status_data_tree,
        old_tree=old_tree,
    )


def _check_trees(
    *,
    parameters: HWSWInventoryParameters,
    inventory_tree: StructuredDataNode,
    status_data_tree: StructuredDataNode,
    old_tree: StructuredDataNode,
) -> Iterator[ActiveCheckResult]:
    if inventory_tree.is_empty() and status_data_tree.is_empty():
        yield ActiveCheckResult(0, "Found no data")
        return

    yield ActiveCheckResult(0, f"Found {inventory_tree.count_entries()} inventory entries")

    swp_table = inventory_tree.get_table(("software", "packages"))
    if swp_table is not None and swp_table.is_empty() and parameters.sw_missing:
        yield ActiveCheckResult(parameters.sw_missing, "software packages information is missing")

    if not _tree_nodes_are_equal(old_tree, inventory_tree, "software"):
        yield ActiveCheckResult(parameters.sw_changes, "software changes")

    if not _tree_nodes_are_equal(old_tree, inventory_tree, "hardware"):
        yield ActiveCheckResult(parameters.hw_changes, "hardware changes")

    if not status_data_tree.is_empty():
        yield ActiveCheckResult(0, f"Found {status_data_tree.count_entries()} status entries")


def _tree_nodes_are_equal(
    old_tree: StructuredDataNode,
    inv_tree: StructuredDataNode,
    edge: str,
) -> bool:
    old_node = old_tree.get_node((edge,))
    inv_node = inv_tree.get_node((edge,))
    if old_node is None:
        return inv_node is None

    if inv_node is None:
        return False

    return old_node.is_equal(inv_node)
