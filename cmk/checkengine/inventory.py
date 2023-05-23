#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import contextlib
import itertools
import time
from collections.abc import Callable, Collection, Container, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.tty as tty
from cmk.utils.log import console, section
from cmk.utils.structured_data import (
    ImmutableTree,
    make_filter_from_choice,
    MutableTree,
    parse_visible_raw_path,
    RawIntervalsFromConfig,
    RetentionIntervals,
    SDPath,
    StructuredDataNode,
    UpdateResult,
)
from cmk.utils.type_defs import (
    HostName,
    ParsedSectionName,
    RuleSetName,
    SectionName,
    ValidatedString,
)

from ._api import FetcherFunction, ParserFunction, SectionPlugin, SummarizerFunction
from ._typedefs import HostKey, SourceType
from .checkresults import ActiveCheckResult
from .host_sections import HostSections
from .sectionparser import (
    filter_out_errors,
    make_providers,
    Provider,
    ResolvedResult,
    store_piggybacked_sections,
)
from .sectionparserutils import check_parsing_errors, get_cache_info, get_section_kwargs

__all__ = [
    "InventoryPluginName",
    "HWSWInventoryParameters",
    "inventorize_cluster",
    "inventorize_host",
    "inventorize_status_data_of_real_host",
    "InventoryPlugin",
    "PInventoryResult",
]


class InventoryPluginName(ValidatedString):
    @classmethod
    def exceptions(cls) -> Container[str]:
        return super().exceptions()


class PInventoryResult(Protocol):
    @property
    def path(self) -> Sequence[str]:
        ...

    def populate_inventory_tree(self, mutable_tree: MutableTree) -> None:
        ...

    def populate_status_data_tree(self, mutable_tree: MutableTree) -> None:
        ...


@dataclass(frozen=True)
class InventoryPlugin:
    sections: Sequence[ParsedSectionName]
    function: Callable[..., Iterable[PInventoryResult]]
    ruleset_name: RuleSetName | None


@dataclass(frozen=True)
class HWSWInventoryParameters:
    hw_changes: int
    sw_changes: int
    sw_missing: int

    # Do not use source states which would overwrite "State when
    # inventory fails" in the ruleset "Do hardware/software Inventory".
    # These are handled by the "Check_MK" service
    fail_status: int
    status_data_inventory: bool

    @classmethod
    def from_raw(cls, raw_parameters: dict) -> HWSWInventoryParameters:
        return cls(
            hw_changes=int(raw_parameters.get("hw-changes", 0)),
            sw_changes=int(raw_parameters.get("sw-changes", 0)),
            sw_missing=int(raw_parameters.get("sw-missing", 0)),
            fail_status=int(raw_parameters.get("inv-fail-status", 1)),
            status_data_inventory=bool(raw_parameters.get("status_data_inventory", False)),
        )


@dataclass(frozen=True)
class CheckInventoryTreeResult:
    processing_failed: bool
    no_data_or_files: bool
    check_result: ActiveCheckResult
    inventory_tree: MutableTree
    update_result: UpdateResult


def inventorize_host(
    host_name: HostName,
    *,
    fetcher: FetcherFunction,
    parser: ParserFunction,
    summarizer: SummarizerFunction,
    inventory_parameters: Callable[[HostName, InventoryPlugin], Mapping[str, object]],
    section_plugins: Mapping[SectionName, SectionPlugin],
    inventory_plugins: Mapping[InventoryPluginName, InventoryPlugin],
    run_plugin_names: Container[InventoryPluginName],
    parameters: HWSWInventoryParameters,
    raw_intervals_from_config: RawIntervalsFromConfig,
    previous_tree: ImmutableTree,
) -> CheckInventoryTreeResult:
    fetched = fetcher(host_name, ip_address=None)
    host_sections = parser((f[0], f[1]) for f in fetched)
    host_sections_no_error = filter_out_errors(host_sections)
    store_piggybacked_sections(host_sections_no_error)

    providers = make_providers(host_sections_no_error, section_plugins)

    mutable_trees, update_result = _inventorize_real_host(
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
        raw_intervals_from_config=raw_intervals_from_config,
        previous_tree=previous_tree,
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
                    inventory_tree=mutable_trees.inventory,
                    status_data_tree=mutable_trees.status_data,
                    previous_tree=previous_tree,
                    processing_failed=processing_failed,
                    no_data_or_files=no_data_or_files,
                ),
                (r for r in summarizer(host_sections) if r.state != 0),
                check_parsing_errors(parsing_errors, error_state=parameters.fail_status),
            )
        ),
        inventory_tree=mutable_trees.inventory,
        update_result=update_result,
    )


def inventorize_cluster(
    nodes: Sequence[HostName],
    *,
    parameters: HWSWInventoryParameters,
    previous_tree: ImmutableTree,
) -> CheckInventoryTreeResult:
    inventory_tree = _inventorize_cluster(nodes=nodes)
    return CheckInventoryTreeResult(
        processing_failed=False,
        no_data_or_files=False,
        check_result=ActiveCheckResult.from_subresults(
            *_check_trees(
                parameters=parameters,
                inventory_tree=inventory_tree,
                status_data_tree=MutableTree(),
                previous_tree=previous_tree,
            ),
        ),
        inventory_tree=inventory_tree,
        update_result=UpdateResult(),
    )


def _inventorize_cluster(*, nodes: Sequence[HostName]) -> MutableTree:
    mutable_tree = MutableTree()
    mutable_tree.add_pairs(
        path=["software", "applications", "check_mk", "cluster"],
        pairs={"is_cluster": True},
    )
    mutable_tree.add_rows(
        path=["software", "applications", "check_mk", "cluster", "nodes"],
        key_columns=["name"],
        rows=[{"name": name} for name in nodes],
    )
    return mutable_tree


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


def _inventorize_real_host(
    *,
    now: int,
    items_of_inventory_plugins: Collection[ItemsOfInventoryPlugin],
    raw_intervals_from_config: RawIntervalsFromConfig,
    previous_tree: ImmutableTree,
) -> tuple[MutableTrees, UpdateResult]:
    section.section_step("Create inventory or status data tree")

    mutable_trees = _create_trees_from_inventory_plugin_items(items_of_inventory_plugins)

    section.section_step("May update inventory tree")

    update_result = _may_update(
        now=now,
        items_of_inventory_plugins=items_of_inventory_plugins,
        raw_intervals_from_config=raw_intervals_from_config,
        inventory_tree=mutable_trees.inventory,
        previous_tree=previous_tree,
    )

    if not mutable_trees.inventory.tree.is_empty():
        mutable_trees.inventory.add_pairs(
            path=["software", "applications", "check_mk", "cluster"],
            pairs={"is_cluster": False},
        )

    return mutable_trees, update_result


def inventorize_status_data_of_real_host(
    host_name: HostName,
    *,
    inventory_parameters: Callable[[HostName, InventoryPlugin], Mapping[str, object]],
    providers: Mapping[HostKey, Provider],
    inventory_plugins: Mapping[InventoryPluginName, InventoryPlugin],
    run_plugin_names: Container[InventoryPluginName],
) -> MutableTree:
    return _create_trees_from_inventory_plugin_items(
        _collect_inventory_plugin_items(
            host_name,
            inventory_parameters=inventory_parameters,
            providers=providers,
            inventory_plugins=inventory_plugins,
            run_plugin_names=run_plugin_names,
        )
    ).status_data


@dataclass(frozen=True)
class ItemsOfInventoryPlugin:
    items: list[PInventoryResult]
    raw_cache_info: tuple[int, int] | None


def _collect_inventory_plugin_items(
    host_name: HostName,
    *,
    inventory_parameters: Callable[[HostName, InventoryPlugin], Mapping[str, object]],
    providers: Mapping[HostKey, Provider],
    inventory_plugins: Mapping[InventoryPluginName, InventoryPlugin],
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
                    for item in inventory_plugin.function(**kwargs)
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


def _parse_inventory_plugin_item(
    item: PInventoryResult, expected_class_name: str
) -> PInventoryResult:
    if item.__class__.__name__ != expected_class_name:
        raise TypeError(
            f"Cannot create {item.__class__.__name__} at path {item.path}:"
            f" this is a {expected_class_name} node."
        )

    return item


@dataclass(frozen=True)
class MutableTrees:
    inventory: MutableTree
    status_data: MutableTree


def _create_trees_from_inventory_plugin_items(
    items_of_inventory_plugins: Iterable[ItemsOfInventoryPlugin],
) -> MutableTrees:
    inventory_tree = MutableTree()
    status_data_tree = MutableTree()
    for items_of_inventory_plugin in items_of_inventory_plugins:
        for item in items_of_inventory_plugin.items:
            item.populate_inventory_tree(inventory_tree)
            item.populate_status_data_tree(status_data_tree)
    return MutableTrees(inventory_tree, status_data_tree)


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
    inventory_tree: MutableTree,
    previous_tree: ImmutableTree,
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

        if (previous_node := previous_tree.tree.get_node(node_path)) is None:
            previous_node = StructuredDataNode()

        if (inventory_node := inventory_tree.tree.get_node(node_path)) is None:
            inventory_node = inventory_tree.tree.setdefault_node(node_path)

        if choices_for_attributes := entry.get("attributes"):
            raw_cache_info = _get_raw_cache_info((node_path, "Attributes"))
            results.append(
                inventory_node.attributes.update_from_previous(
                    now,
                    previous_node.attributes,
                    make_filter_from_choice(choices_for_attributes),
                    RetentionIntervals(
                        cached_at=raw_cache_info[0],
                        cache_interval=raw_cache_info[1],
                        retention_interval=entry["interval"],
                    ),
                )
            )

        elif choices_for_table := entry.get("columns"):
            raw_cache_info = _get_raw_cache_info((node_path, "TableRow"))
            results.append(
                inventory_node.table.update_from_previous(
                    now,
                    previous_node.table,
                    make_filter_from_choice(choices_for_table),
                    RetentionIntervals(
                        cached_at=raw_cache_info[0],
                        cache_interval=raw_cache_info[1],
                        retention_interval=entry["interval"],
                    ),
                )
            )

    return UpdateResult.from_results(results)


def _check_fetched_data_or_trees(
    *,
    parameters: HWSWInventoryParameters,
    inventory_tree: MutableTree,
    status_data_tree: MutableTree,
    previous_tree: ImmutableTree,
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
            inventory_tree.tree.count_entries() == 1
            and (
                cluster_attributes := inventory_tree.tree.get_attributes(
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
        previous_tree=previous_tree,
    )


def _check_trees(
    *,
    parameters: HWSWInventoryParameters,
    inventory_tree: MutableTree,
    status_data_tree: MutableTree,
    previous_tree: ImmutableTree,
) -> Iterator[ActiveCheckResult]:
    if inventory_tree.tree.is_empty() and status_data_tree.tree.is_empty():
        yield ActiveCheckResult(0, "Found no data")
        return

    yield ActiveCheckResult(0, f"Found {inventory_tree.tree.count_entries()} inventory entries")

    swp_table = inventory_tree.tree.get_table(("software", "packages"))
    if swp_table is not None and swp_table.is_empty() and parameters.sw_missing:
        yield ActiveCheckResult(parameters.sw_missing, "software packages information is missing")

    if not _tree_nodes_are_equal(previous_tree, inventory_tree, "software"):
        yield ActiveCheckResult(parameters.sw_changes, "software changes")

    if not _tree_nodes_are_equal(previous_tree, inventory_tree, "hardware"):
        yield ActiveCheckResult(parameters.hw_changes, "hardware changes")

    if not status_data_tree.tree.is_empty():
        yield ActiveCheckResult(0, f"Found {status_data_tree.tree.count_entries()} status entries")


def _tree_nodes_are_equal(
    previous_tree: ImmutableTree,
    inventory_tree: MutableTree,
    edge: str,
) -> bool:
    previous_node = previous_tree.tree.get_node((edge,))
    inventory_node = inventory_tree.tree.get_node((edge,))
    if previous_node is None:
        return inventory_node is None

    if inventory_node is None:
        return False

    return previous_node.is_equal(inventory_node)
