#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import NamedTuple

import cmk.utils.paths
from cmk.base.errorhandling import (
    create_section_crash_dump,
    RecordingFetcher,
)
from cmk.ccc.hostaddress import HostName, Hosts
from cmk.checkengine import inventory
from cmk.checkengine.auto_queue import AutoQueue
from cmk.checkengine.discovery import DiscoverySettings, is_inventorized
from cmk.checkengine.fetcher_abc import FetcherFunction
from cmk.checkengine.inventory import HWSWInventoryParameters
from cmk.checkengine.parser import (
    ParserFunction,
)
from cmk.checkengine.plugins import (
    InventoryPlugin,
    InventoryPluginName,
    SectionName,
)
from cmk.checkengine.sectionparser import SectionPlugin
from cmk.checkengine.specs.checkresults import ActiveCheckResult
from cmk.checkengine.summarize import SummarizerFunction
from cmk.inventory.label_picker import InventorizedHostLabelsStore, LabelPickerConfig, pick_labels
from cmk.inventory.paths import InventoryPaths
from cmk.inventory.store import InventoryStore, make_meta
from cmk.inventory.trees import (
    ImmutableTree,
    MutableTree,
    RawIntervalFromConfig,
    SDPath,
)
from cmk.ruleset_matcher.labels import DiscoveredHostLabelsStore
from cmk.utils.everythingtype import EVERYTHING
from cmk.utils.log import console


class _SaveTreeActions(NamedTuple):
    do_archive: bool
    do_save: bool


def _render_update_results(
    update_results: Mapping[SDPath, Sequence[str]],
) -> str:
    lines = ["Updated inventory tree:"]
    for path, messages in update_results.items():
        lines.append(f"  Path '{' > '.join(path)}':")
        lines.extend(f"    {r}" for r in sorted(messages))
    return "\n".join(lines) + "\n"


def _get_save_tree_actions(
    *,
    previous_tree: ImmutableTree,
    inventory_tree: MutableTree,
) -> _SaveTreeActions:
    if not inventory_tree:
        # Archive current inventory tree file if it exists. Important for host inventory icon
        console.verbose("No inventory tree.")
        return _SaveTreeActions(do_archive=True, do_save=False)

    if not previous_tree:
        console.verbose("New inventory tree.")
        return _SaveTreeActions(do_archive=False, do_save=True)

    if has_changed := previous_tree != inventory_tree:
        console.verbose("Inventory tree has changed.")

    if update_results := inventory_tree.get_update_results():
        console.verbose_no_lf(_render_update_results(update_results))

    return _SaveTreeActions(
        do_archive=has_changed,
        do_save=(has_changed or len(update_results) > 0),
    )


def _schedule_host_labels_rediscovery(
    host_name: HostName,
    *,
    labels_differ: bool,
    rediscovery: DiscoverySettings,
    autodiscovery_dir: Path,
) -> Iterator[ActiveCheckResult]:
    if labels_differ and rediscovery.update_host_labels:
        AutoQueue(autodiscovery_dir).add(host_name)
        yield ActiveCheckResult(state=0, summary="Rediscovery scheduled")


def execute_active_check_inventory(
    host_name: HostName,
    *,
    hosts_config: Hosts,
    fetcher: FetcherFunction,
    parser: ParserFunction,
    summarizer: SummarizerFunction,
    section_plugins: Mapping[SectionName, SectionPlugin],
    inventory_plugins: Mapping[InventoryPluginName, InventoryPlugin],
    inventory_parameters: Callable[[HostName, InventoryPlugin], Mapping[str, object]],
    parameters: HWSWInventoryParameters,
    raw_intervals_from_config: Sequence[RawIntervalFromConfig],
    label_picker_configs: Sequence[LabelPickerConfig],
    rediscovery: DiscoverySettings,
    inventorized_host_labels_dir: Path,
    discovered_host_labels_dir: Path,
    autodiscovery_dir: Path,
    debug: bool,
) -> Sequence[ActiveCheckResult]:
    inv_store = InventoryStore(cmk.utils.paths.omd_root)
    previous_tree = inv_store.load_previous_inventory_tree(host_name=host_name)

    if host_name in hosts_config.clusters:
        result = inventory.inventorize_cluster(
            hosts_config.clusters[host_name],
            parameters=parameters,
            previous_tree=previous_tree,
        )
    else:
        recording_fetcher = RecordingFetcher(fetcher)
        result = inventory.inventorize_host(
            host_name,
            omd_root=cmk.utils.paths.omd_root,
            fetcher=recording_fetcher,
            parser=parser,
            summarizer=summarizer,
            inventory_parameters=inventory_parameters,
            section_plugins=section_plugins,
            section_error_handling=lambda section_name, raw_data: create_section_crash_dump(
                operation="parsing",
                section_name=section_name,
                section_content=raw_data,
                host_name=host_name,
                get_agent_output=lambda: recording_fetcher.serialized(host_name),
            ),
            inventory_plugins=inventory_plugins,
            run_plugin_names=EVERYTHING,
            parameters=parameters,
            raw_intervals_from_config=raw_intervals_from_config,
            previous_tree=previous_tree,
            debug=debug,
        )

    inv_paths = InventoryPaths(cmk.utils.paths.omd_root)
    if result.no_data_or_files:
        AutoQueue(inv_paths.auto_dir).add(host_name)
    else:
        AutoQueue(inv_paths.auto_dir).remove(host_name)

    if not (result.processing_failed or result.no_data_or_files):
        save_tree_actions = _get_save_tree_actions(
            previous_tree=previous_tree,
            inventory_tree=result.inventory_tree,
        )
        # The order of archive or save is important:
        if save_tree_actions.do_archive:
            console.verbose("Archive current inventory tree.")
            inv_store.archive_inventory_tree(host_name=host_name)
        if save_tree_actions.do_save:
            console.verbose("Save new inventory tree.")
            inv_store.save_inventory_tree(
                host_name=host_name,
                tree=result.inventory_tree,
                meta=make_meta(do_archive=save_tree_actions.do_archive),
            )

    if host_name in hosts_config.clusters:
        return result.check_results

    labels_store = InventorizedHostLabelsStore(host_name, inventorized_host_labels_dir)
    if not (result.processing_failed or result.no_data_or_files):
        labels_store.save(pick_labels(result.inventory_tree, label_picker_configs))
    label_results = inventory.check_inventorized_host_labels(
        parameters=parameters,
        picked=labels_store.load(),
        accepted={
            label.name: label.value
            for label in DiscoveredHostLabelsStore(host_name, discovered_host_labels_dir).load()
            if is_inventorized(label)
        },
    )
    return [
        *result.check_results,
        *label_results,
        *_schedule_host_labels_rediscovery(
            host_name,
            labels_differ=bool(label_results),
            rediscovery=rediscovery,
            autodiscovery_dir=autodiscovery_dir,
        ),
    ]
