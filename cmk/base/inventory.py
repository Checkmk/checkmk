#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterator, Mapping, Sequence
from pathlib import Path

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
from cmk.inventory.config import LabelPickerConfig, RawIntervalFromConfig
from cmk.inventory.label_picker import InventorizedHostLabelsStore, pick_labels
from cmk.inventory.paths import InventoryPaths
from cmk.inventory.store import InventoryStore
from cmk.ruleset_matcher.labels import DiscoveredHostLabelsStore
from cmk.utils.everythingtype import EVERYTHING
from cmk.utils.log import console


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
    previous_tree = inv_store.load_previous_inventory_tree(host_name=host_name, debug=debug)

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
                debug=debug,
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
        for message in inv_store.save_if_changed(
            host_name=host_name,
            previous_tree=previous_tree,
            tree=result.inventory_tree,
            debug=debug,
        ):
            console.verbose(message)

    if host_name in hosts_config.clusters:
        return result.check_results

    labels_store = InventorizedHostLabelsStore(host_name, inventorized_host_labels_dir)
    if not (result.processing_failed or result.no_data_or_files):
        labels_store.save(pick_labels(result.inventory_tree, label_picker_configs))
    label_results = inventory.check_inventorized_host_labels(
        parameters=parameters,
        picked=labels_store.load(debug=debug),
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
