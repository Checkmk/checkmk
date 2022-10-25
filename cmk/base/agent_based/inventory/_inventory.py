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
from typing import Container, Iterable, NamedTuple, Sequence, Tuple

import cmk.utils.tty as tty
from cmk.utils.cpu_tracking import Snapshot
from cmk.utils.exceptions import OnError
from cmk.utils.log import console
from cmk.utils.structured_data import StructuredDataNode
from cmk.utils.type_defs import AgentRawData, InventoryPluginName, result

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
from cmk.base.agent_based.utils import get_section_kwargs
from cmk.base.config import HostConfig
from cmk.base.sources import fetch_all, make_sources

from ._retentions import RetentionsTracker
from ._tree_aggregator import InventoryTrees, TreeAggregator

__all__ = ["inventorize_cluster", "fetch_real_host_data", "inventorize_real_host"]


class FetchedDataResult(NamedTuple):
    parsed_sections_broker: ParsedSectionsBroker
    source_results: SourceResults
    parsing_errors: Sequence[str]
    processing_failed: bool


def inventorize_cluster(*, host_config: HostConfig) -> InventoryTrees:
    inventory_tree = StructuredDataNode()

    _set_cluster_property(inventory_tree, is_cluster=True)

    if not (nodes := host_config.nodes):
        return InventoryTrees(inventory_tree, StructuredDataNode())

    node = inventory_tree.setdefault_node(
        ("software", "applications", "check_mk", "cluster", "nodes")
    )
    node.table.add_key_columns(["name"])
    node.table.add_rows([{"name": node_name} for node_name in nodes])

    return InventoryTrees(inventory_tree, StructuredDataNode())


def fetch_real_host_data(
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


def inventorize_real_host(
    *,
    host_config: HostConfig,
    parsed_sections_broker: ParsedSectionsBroker,
    run_plugin_names: Container[InventoryPluginName],
    retentions_tracker: RetentionsTracker,
) -> InventoryTrees:
    tree_aggregator = TreeAggregator()

    _set_cluster_property(tree_aggregator.trees.inventory, is_cluster=False)

    section.section_step("Executing inventory plugins")
    for inventory_plugin in agent_based_register.iter_all_inventory_plugins():
        if inventory_plugin.name not in run_plugin_names:
            continue

        for host_key in (host_config.host_key, host_config.host_key_mgmt):
            kwargs = get_section_kwargs(
                parsed_sections_broker,
                host_key,
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
                retentions_tracker=retentions_tracker,
                raw_cache_info=parsed_sections_broker.get_cache_info(inventory_plugin.sections),
                is_legacy_plugin=inventory_plugin.module is None,
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
    return tree_aggregator.trees


def _set_cluster_property(
    inventory_tree: StructuredDataNode,
    *,
    is_cluster: bool,
) -> None:
    node = inventory_tree.setdefault_node(("software", "applications", "check_mk", "cluster"))
    node.attributes.add_pairs({"is_cluster": is_cluster})
