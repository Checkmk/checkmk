#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module is the main entry point for the inventory tree creation/deletion of hosts.

CL:
- 'cmk -i[i] ...' is intended to be a kind of preview and does not store any trees.
- 'cmk --inventory-as-check ...' is the related command of the HW/SW Inventory service,
    ie. a tree is created, stored and compared to the old one if it exists,
    if and only if there are NO errors while executing inventory plugins.
"""

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Container, Iterable, Iterator, NamedTuple, Sequence, Tuple

import cmk.utils.paths
import cmk.utils.tty as tty
from cmk.utils.check_utils import ActiveCheckResult
from cmk.utils.cpu_tracking import Snapshot
from cmk.utils.exceptions import OnError
from cmk.utils.log import console
from cmk.utils.structured_data import StructuredDataNode, UpdateResult
from cmk.utils.type_defs import AgentRawData, HostKey, InventoryPluginName, result, SourceType

from cmk.snmplib.type_defs import SNMPRawData

from cmk.core_helpers.host_sections import HostSections
from cmk.core_helpers.type_defs import Mode, NO_SELECTION, SectionNameCollection, SourceInfo

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.config as config
import cmk.base.section as section
from cmk.base.agent_based.data_provider import (
    make_broker,
    parse_messages,
    ParsedSectionsBroker,
    SourceResults,
    store_piggybacked_sections,
)
from cmk.base.agent_based.utils import (
    check_parsing_errors,
    get_section_kwargs,
    summarize_host_sections,
)
from cmk.base.config import HostConfig
from cmk.base.sources import fetch_all, make_sources

from ._tree_aggregator import ClusterTreeAggregator, RealHostTreeAggregator

__all__ = [
    "inventorize_real_host_via_plugins",
    "check_inventory_tree",
]


class FetchedDataResult(NamedTuple):
    parsed_sections_broker: ParsedSectionsBroker
    source_results: SourceResults
    parsing_errors: Sequence[str]
    processing_failed: bool
    no_data_or_files: bool


@dataclass(frozen=True)
class CheckInventoryTreeResult:
    processing_failed: bool
    no_data_or_files: bool
    check_result: ActiveCheckResult
    inventory_tree: StructuredDataNode
    update_result: UpdateResult


def check_inventory_tree(
    *,
    host_config: HostConfig,
    selected_sections: SectionNameCollection,
    run_plugin_names: Container[InventoryPluginName],
    parameters: config.HWSWInventoryParameters,
    old_tree: StructuredDataNode,
) -> CheckInventoryTreeResult:
    tree_aggregator: ClusterTreeAggregator | RealHostTreeAggregator
    if host_config.is_cluster:
        tree_aggregator = ClusterTreeAggregator()
        tree_aggregator.add_cluster_properties(nodes=host_config.nodes or [])
        return CheckInventoryTreeResult(
            processing_failed=False,
            no_data_or_files=False,
            check_result=ActiveCheckResult.from_subresults(
                *_check_trees(
                    parameters=parameters,
                    inventory_tree=tree_aggregator.inventory_tree,
                    status_data_tree=StructuredDataNode(),
                    old_tree=old_tree,
                ),
            ),
            inventory_tree=tree_aggregator.inventory_tree,
            update_result=UpdateResult(save_tree=False, reason=""),
        )

    fetched_data_result = _fetch_real_host_data(
        host_config=host_config,
        selected_sections=selected_sections,
    )

    tree_aggregator = _inventorize_real_host(
        host_config=host_config,
        parsed_sections_broker=fetched_data_result.parsed_sections_broker,
        run_plugin_names=run_plugin_names,
        old_tree=old_tree,
    )

    return CheckInventoryTreeResult(
        processing_failed=fetched_data_result.processing_failed,
        no_data_or_files=fetched_data_result.no_data_or_files,
        check_result=ActiveCheckResult.from_subresults(
            *_check_fetched_data_or_trees(
                parameters=parameters,
                fetched_data_result=fetched_data_result,
                inventory_tree=tree_aggregator.inventory_tree,
                status_data_tree=tree_aggregator.status_data_tree,
                old_tree=old_tree,
            ),
            *summarize_host_sections(
                source_results=fetched_data_result.source_results,
                # Do not use source states which would overwrite "State when inventory fails" in the
                # ruleset "Do hardware/software Inventory". These are handled by the "Check_MK" service
                override_non_ok_state=parameters.fail_status,
                exit_spec_cb=host_config.exit_code_spec,
                time_settings_cb=lambda hostname: config.get_config_cache().get_piggybacked_hosts_time_settings(
                    piggybacked_hostname=hostname,
                ),
                is_piggyback=host_config.is_piggyback_host,
            ),
            *check_parsing_errors(
                errors=fetched_data_result.parsing_errors,
                error_state=parameters.fail_status,
            ),
        ),
        inventory_tree=tree_aggregator.inventory_tree,
        update_result=tree_aggregator.update_result,
    )


def _fetch_real_host_data(
    *,
    host_config: HostConfig,
    selected_sections: SectionNameCollection,
) -> FetchedDataResult:
    ipaddress = config.lookup_ip_address(host_config)
    config_cache = config.get_config_cache()

    fetched: Sequence[
        Tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception], Snapshot]
    ] = fetch_all(
        make_sources(
            host_config,
            ipaddress,
            ip_lookup=lambda host_name: config.lookup_ip_address(
                config_cache.get_host_config(host_name)
            ),
            selected_sections=selected_sections,
            force_snmp_cache_refresh=False,
            on_scan_error=OnError.RAISE,
            simulation_mode=config.simulation_mode,
            missing_sys_description=config.get_config_cache().in_binary_hostlist(
                host_config.hostname,
                config.snmp_without_sys_descr,
            ),
            file_cache_max_age=host_config.max_cachefile_age,
        ),
        mode=(Mode.INVENTORY if selected_sections is NO_SELECTION else Mode.FORCE_SECTIONS),
    )
    host_sections, results = parse_messages(
        ((f[0], f[1]) for f in fetched),
        selected_sections=selected_sections,
        logger=logging.getLogger("cmk.base.inventory"),
    )
    store_piggybacked_sections(host_sections)
    broker = make_broker(host_sections)

    parsing_errors = broker.parsing_errors()
    return FetchedDataResult(
        parsed_sections_broker=broker,
        source_results=results,
        parsing_errors=parsing_errors,
        processing_failed=(
            _sources_failed(host_section for _source, host_section in results)
            or bool(parsing_errors)
        ),
        no_data_or_files=_no_data_or_files(host_config, host_sections.values()),
    )


def _sources_failed(
    host_sections: Iterable[result.Result[HostSections, Exception]],
) -> bool:
    """Check if data sources of a host failed

    If a data source failed, we may have incomlete data. In that case we
    may not write it to disk because that would result in a flapping state
    of the tree, which would blow up the inventory history (in terms of disk usage).
    """
    # If a result is not OK, that means the corresponding sections have not been added.
    return any(not host_section.is_ok() for host_section in host_sections)


def _no_data_or_files(host_config: HostConfig, host_sections: Iterable[HostSections]) -> bool:
    host_name = host_config.hostname

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
    host_config: HostConfig,
    parsed_sections_broker: ParsedSectionsBroker,
    run_plugin_names: Container[InventoryPluginName],
    old_tree: StructuredDataNode,
) -> RealHostTreeAggregator:
    tree_aggregator = inventorize_real_host_via_plugins(
        host_config=host_config,
        parsed_sections_broker=parsed_sections_broker,
        run_plugin_names=run_plugin_names,
    )

    tree_aggregator.may_update(now=int(time.time()), previous_tree=old_tree)

    if not tree_aggregator.inventory_tree.is_empty():
        tree_aggregator.add_cluster_property()

    return tree_aggregator


def inventorize_real_host_via_plugins(
    *,
    host_config: HostConfig,
    parsed_sections_broker: ParsedSectionsBroker,
    run_plugin_names: Container[InventoryPluginName],
) -> RealHostTreeAggregator:
    tree_aggregator = RealHostTreeAggregator(host_config.inv_retention_intervals)

    section.section_step("Executing inventory plugins")
    for inventory_plugin in agent_based_register.iter_all_inventory_plugins():
        if inventory_plugin.name not in run_plugin_names:
            continue

        for source_type in (SourceType.HOST, SourceType.MANAGEMENT):
            kwargs = get_section_kwargs(
                parsed_sections_broker,
                HostKey(host_config.hostname, source_type),
                inventory_plugin.sections,
            )
            if not kwargs:
                console.vverbose(
                    " %s%s%s%s: skipped (no data)\n",
                    tty.yellow,
                    tty.bold,
                    inventory_plugin.name,
                    tty.normal,
                )
                continue

            # Inventory functions can optionally have a second argument: parameters.
            # These are configured via rule sets (much like check parameters).
            if inventory_plugin.inventory_ruleset_name is not None:
                kwargs = {
                    **kwargs,
                    "params": host_config.inventory_parameters(
                        inventory_plugin.inventory_ruleset_name
                    ),
                }

            exception = tree_aggregator.aggregate_results(
                inventory_generator=inventory_plugin.inventory_function(**kwargs),
                raw_cache_info=parsed_sections_broker.get_cache_info(inventory_plugin.sections),
            )

            if exception:
                console.warning(
                    " %s%s%s%s: failed: %s",
                    tty.red,
                    tty.bold,
                    inventory_plugin.name,
                    tty.normal,
                    exception,
                )
            else:
                console.verbose(" %s%s%s%s", tty.green, tty.bold, inventory_plugin.name, tty.normal)
                console.vverbose(": ok\n")

    console.verbose("\n")
    return tree_aggregator


def _check_fetched_data_or_trees(
    *,
    parameters: config.HWSWInventoryParameters,
    fetched_data_result: FetchedDataResult,
    inventory_tree: StructuredDataNode,
    status_data_tree: StructuredDataNode,
    old_tree: StructuredDataNode,
) -> Iterator[ActiveCheckResult]:
    if fetched_data_result.no_data_or_files:
        yield ActiveCheckResult(0, "No data yet, please be patient")
        return

    if fetched_data_result.processing_failed:
        yield ActiveCheckResult(parameters.fail_status, "Cannot update tree")

    yield from _check_trees(
        parameters=parameters,
        inventory_tree=inventory_tree,
        status_data_tree=status_data_tree,
        old_tree=old_tree,
    )


def _check_trees(
    *,
    parameters: config.HWSWInventoryParameters,
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
