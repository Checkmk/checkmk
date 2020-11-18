#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Currently this module manages the inventory tree which is built
while the inventory is performed for one host.

In the future all inventory code should be moved to this module."""

import os
from typing import (
    Dict,
    Hashable,
    List,
    Literal,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)
from contextlib import suppress

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.misc
import cmk.utils.paths
import cmk.utils.store as store
import cmk.utils.tty as tty
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.log import console
from cmk.utils.structured_data import StructuredDataTree
from cmk.utils.type_defs import (
    HostAddress,
    HostName,
    InventoryPluginName,
    MetricTuple,
    result,
    SectionName,
    ServiceAdditionalDetails,
    ServiceDetails,
    ServiceState,
    SourceType,
)

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.check_api_utils as check_api_utils
import cmk.base.config as config
import cmk.base.checkers as checkers
import cmk.base.decorator
import cmk.base.ip_lookup as ip_lookup
import cmk.base.section as section

from cmk.base.api.agent_based.inventory_classes import (
    AttrDict,
    Attributes,
    TableRow,
    InventoryResult,
)
from cmk.base.checkers import HostSections, Source
from cmk.base.checkers.host_sections import HostKey, MultiHostSections


class InventoryTrees(NamedTuple):
    inventory: StructuredDataTree
    status_data: StructuredDataTree


class ActiveInventoryResult(NamedTuple):
    trees: InventoryTrees
    source_results: Sequence[Tuple[Source, result.Result[HostSections, Exception]]]
    safe_to_write: bool


#.
#   .--Inventory-----------------------------------------------------------.
#   |            ___                      _                                |
#   |           |_ _|_ ____   _____ _ __ | |_ ___  _ __ _   _              |
#   |            | || '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |             |
#   |            | || | | \ V /  __/ | | | || (_) | |  | |_| |             |
#   |           |___|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |             |
#   |                                                   |___/              |
#   +----------------------------------------------------------------------+
#   | Code for doing the actual inventory                                  |
#   '----------------------------------------------------------------------'


def do_inv(
    hostnames: List[HostName],
    *,
    preselected_section_names: Optional[Set[SectionName]] = None,
    run_only_plugin_names: Optional[Set[InventoryPluginName]] = None,
) -> None:
    store.makedirs(cmk.utils.paths.inventory_output_dir)
    store.makedirs(cmk.utils.paths.inventory_archive_dir)

    for hostname in hostnames:
        section.section_begin(hostname)
        try:
            host_config = config.HostConfig.make_host_config(hostname)
            inv_result = _do_active_inventory_for(
                host_config=host_config,
                preselected_section_names=preselected_section_names,
                run_only_plugin_names=run_only_plugin_names,
            )

            _run_inventory_export_hooks(host_config, inv_result.trees.inventory)
            # TODO: inv_results.source_results is completely ignored here.
            # We should process the results to make errors visible on the console
            _show_inventory_results_on_console(inv_result.trees)

        except Exception as e:
            if cmk.utils.debug.enabled():
                raise

            section.section_error("%s" % e)
        finally:
            cmk.utils.cleanup.cleanup_globals()


def _show_inventory_results_on_console(trees: InventoryTrees) -> None:
    section.section_success("Found %s%s%d%s inventory entries" %
                            (tty.bold, tty.yellow, trees.inventory.count_entries(), tty.normal))
    section.section_success("Found %s%s%d%s status entries" %
                            (tty.bold, tty.yellow, trees.status_data.count_entries(), tty.normal))


@cmk.base.decorator.handle_check_mk_check_result("check_mk_active-cmk_inv",
                                                 "Check_MK HW/SW Inventory")
def do_inv_check(
    hostname: HostName, options: Dict[str, int]
) -> Tuple[ServiceState, List[ServiceDetails], List[ServiceAdditionalDetails], List[MetricTuple]]:
    _inv_hw_changes = options.get("hw-changes", 0)
    _inv_sw_changes = options.get("sw-changes", 0)
    _inv_sw_missing = options.get("sw-missing", 0)
    _inv_fail_status = options.get("inv-fail-status", 1)

    host_config = config.HostConfig.make_host_config(hostname)

    inv_result = _do_active_inventory_for(
        host_config=host_config,
        preselected_section_names=None,
        run_only_plugin_names=None,
    )
    trees = inv_result.trees

    status = 0
    infotexts: List[str] = []
    long_infotexts: List[str] = []

    if inv_result.safe_to_write:
        old_tree = _save_inventory_tree(hostname, trees.inventory)
    else:
        old_tree, sources_state = None, 1
        status = max(status, sources_state)
        infotexts.append("Cannot update tree%s" % check_api_utils.state_markers[sources_state])

    _run_inventory_export_hooks(host_config, trees.inventory)

    if trees.inventory.is_empty() and trees.status_data.is_empty():
        infotexts.append("Found no data")

    else:
        infotexts.append("Found %d inventory entries" % trees.inventory.count_entries())

        # Node 'software' is always there because _do_inv_for creates this node for cluster info
        if not trees.inventory.get_sub_container(['software']).has_edge('packages')\
           and _inv_sw_missing:
            infotexts.append("software packages information is missing" +
                             check_api_utils.state_markers[_inv_sw_missing])
            status = max(status, _inv_sw_missing)

        if old_tree is not None:
            if not old_tree.is_equal(trees.inventory, edges=["software"]):
                infotext = "software changes"
                if _inv_sw_changes:
                    status = max(status, _inv_sw_changes)
                    infotext += check_api_utils.state_markers[_inv_sw_changes]
                infotexts.append(infotext)

            if not old_tree.is_equal(trees.inventory, edges=["hardware"]):
                infotext = "hardware changes"
                if _inv_hw_changes:
                    status = max(status, _inv_hw_changes)
                    infotext += check_api_utils.state_markers[_inv_hw_changes]

                infotexts.append(infotext)

        if not trees.status_data.is_empty():
            infotexts.append("Found %s status entries" % trees.status_data.count_entries())

    for source, host_sections in inv_result.source_results:
        source_state, source_output, _source_perfdata = source.summarize(host_sections)
        if source_state != 0:
            # Do not output informational things (state == 0). Also do not use source states
            # which would overwrite "State when inventory fails" in the ruleset
            # "Do hardware/software Inventory".
            # These information and source states are handled by the "Check_MK" service
            status = max(_inv_fail_status, status)
            infotexts.append("[%s] %s" % (source.id, source_output))

    return status, infotexts, long_infotexts, []


def _do_active_inventory_for(
    *,
    host_config: config.HostConfig,
    preselected_section_names: Optional[Set[SectionName]],
    run_only_plugin_names: Optional[Set[InventoryPluginName]],
) -> ActiveInventoryResult:
    if host_config.is_cluster:
        return ActiveInventoryResult(
            trees=_do_inv_for_cluster(host_config),
            source_results=[],
            safe_to_write=True,
        )

    ipaddress = ip_lookup.lookup_ip_address(host_config)
    config_cache = config.get_config_cache()

    multi_host_sections, source_results = _fetch_multi_host_sections_for_inv(
        config_cache,
        host_config,
        ipaddress,
        preselected_section_names,
    )

    return ActiveInventoryResult(
        trees=_do_inv_for_realhost(
            host_config,
            ipaddress,
            multi_host_sections=multi_host_sections,
            run_only_plugin_names=run_only_plugin_names,
        ),
        source_results=source_results,
        safe_to_write=_safe_to_write_tree(source_results) and preselected_section_names is None,
    )


def _fetch_multi_host_sections_for_inv(
    config_cache: config.ConfigCache,
    host_config: config.HostConfig,
    ipaddress: Optional[HostAddress],
    preselected_sections: Optional[Set[SectionName]],
) -> Tuple[MultiHostSections, Sequence[Tuple[Source, result.Result[HostSections, Exception]]]]:
    if host_config.is_cluster:
        return MultiHostSections(), []

    mode = checkers.Mode.INVENTORY if preselected_sections is None else checkers.Mode.FORCE_SECTIONS

    sources = checkers.make_sources(
        host_config,
        ipaddress,
        mode=mode,
        preselected_sections=preselected_sections,
    )
    for source in sources:
        _configure_source_for_inv(source)

    nodes = checkers.make_nodes(
        config_cache,
        host_config,
        ipaddress,
        mode,
        sources,
    )
    multi_host_sections = MultiHostSections()
    results = checkers.update_host_sections(
        multi_host_sections,
        nodes,
        max_cachefile_age=host_config.max_cachefile_age,
        host_config=host_config,
        fetcher_messages=list(
            checkers.fetch_all(
                nodes,
                max_cachefile_age=host_config.max_cachefile_age,
                host_config=host_config,
            )),
    )

    return multi_host_sections, results


def _configure_source_for_inv(source: checkers.Source):
    if isinstance(source, checkers.snmp.SNMPSource):
        source.use_snmpwalk_cache = False
        checkers.FileCacheFactory.snmp_disabled = True


def _safe_to_write_tree(
    results: Sequence[Tuple[Source, result.Result[HostSections, Exception]]],) -> bool:
    """Check if data sources of a host failed

    If a data source failed, we may have incomlete data. In that case we
    may not write it to disk because that would result in a flapping state
    of the tree, which would blow up the inventory history (in terms of disk usage).
    """
    # If a result is not OK, that means the corresponding sections have not been added.
    return all(source_result.is_ok() for _source, source_result in results)


def do_inventory_actions_during_checking_for(
    config_cache: config.ConfigCache,
    host_config: config.HostConfig,
    ipaddress: Optional[HostAddress],
    *,
    multi_host_sections: MultiHostSections,
) -> None:

    if not host_config.do_status_data_inventory:
        # includes cluster case
        _cleanup_status_data(host_config.hostname)
        return  # nothing to do here

    trees = _do_inv_for_realhost(
        host_config,
        ipaddress,
        multi_host_sections=multi_host_sections,
        run_only_plugin_names=None,
    )
    _save_status_data_tree(host_config.hostname, trees.status_data)


def _cleanup_status_data(hostname: HostName) -> None:
    """Remove empty status data files"""
    filepath = "%s/%s" % (cmk.utils.paths.status_data_dir, hostname)
    with suppress(OSError):
        os.remove(filepath)
    with suppress(OSError):
        os.remove(filepath + ".gz")


def _do_inv_for_cluster(host_config: config.HostConfig) -> InventoryTrees:
    inventory_tree = StructuredDataTree()
    _set_cluster_property(inventory_tree, host_config)

    if not host_config.nodes:
        return InventoryTrees(inventory_tree, StructuredDataTree())

    inv_node = inventory_tree.get_list("software.applications.check_mk.cluster.nodes:")
    for node_name in host_config.nodes:
        inv_node.append({
            "name": node_name,
        })

    inventory_tree.normalize_nodes()
    return InventoryTrees(inventory_tree, StructuredDataTree())


def _do_inv_for_realhost(
    host_config: config.HostConfig,
    ipaddress: Optional[HostAddress],
    *,
    multi_host_sections: MultiHostSections,
    run_only_plugin_names: Optional[Set[InventoryPluginName]],
) -> InventoryTrees:
    tree_aggregator = _TreeAggregator()
    _set_cluster_property(tree_aggregator.trees.inventory, host_config)

    section.section_step("Executing inventory plugins")
    console.verbose("Plugins:")
    for inventory_plugin in agent_based_register.iter_all_inventory_plugins():
        if run_only_plugin_names and inventory_plugin.name not in run_only_plugin_names:
            continue

        kwargs = multi_host_sections.get_section_kwargs(
            HostKey(host_config.hostname, ipaddress, SourceType.HOST),
            inventory_plugin.sections,
        )
        if not kwargs:
            continue

        console.verbose(" %s%s%s%s" % (tty.green, tty.bold, inventory_plugin.name, tty.normal))

        # Inventory functions can optionally have a second argument: parameters.
        # These are configured via rule sets (much like check parameters).
        if inventory_plugin.inventory_ruleset_name is not None:
            kwargs["params"] = host_config.inventory_parameters(
                str(inventory_plugin.inventory_ruleset_name))  # TODO (mo): keep type!

        tree_aggregator.aggregate_results(
            inventory_plugin.inventory_function(**kwargs),
            inventory_plugin.name,
        )

    console.verbose("\n")

    tree_aggregator.trees.inventory.normalize_nodes()
    tree_aggregator.trees.status_data.normalize_nodes()
    return tree_aggregator.trees


def _set_cluster_property(
    inventory_tree: StructuredDataTree,
    host_config: config.HostConfig,
) -> None:
    inventory_tree.get_dict(
        "software.applications.check_mk.cluster.")["is_cluster"] = host_config.is_cluster


class _TreeAggregator:
    def __init__(self):
        self.trees = InventoryTrees(
            inventory=StructuredDataTree(),
            status_data=StructuredDataTree(),
        )
        self._index_cache = {}

    def aggregate_results(
        self,
        inventory_generator: InventoryResult,
        plugin_name: InventoryPluginName,
    ) -> None:

        try:
            inventory_items = list(inventory_generator)
        except Exception as exc:
            if cmk.utils.debug.enabled():
                raise
            console.warning(f"Error in inventory plugin {plugin_name}: {exc}")
            return

        for item in inventory_items:
            if isinstance(item, Attributes):
                self._integrate_attributes(item)
            elif isinstance(item, TableRow):
                self._integrate_table_row(item)
            else:  # can't happen
                raise NotImplementedError()

    def _integrate_attributes(
        self,
        attributes: Attributes,
    ) -> None:

        leg_path = ".".join(attributes.path) + "."
        if attributes.inventory_attributes:
            self.trees.inventory.get_dict(leg_path).update(attributes.inventory_attributes)
        if attributes.status_attributes:
            self.trees.status_data.get_dict(leg_path).update(attributes.status_attributes)

    @staticmethod
    def _make_row_key(key_columns: AttrDict) -> Hashable:
        return tuple(sorted(key_columns.items()))

    def _get_row(
        self,
        path: str,
        tree_name: Literal["inventory", "status_data"],
        row_key: Hashable,
        key_columns: AttrDict,
    ) -> Dict[str, Union[None, int, float, str]]:
        """Find matching table row or create one"""
        table = getattr(self.trees, tree_name).get_list(path)

        new_row_index = len(table)  # index should we need to create a new row
        use_index = self._index_cache.setdefault((path, tree_name, row_key), new_row_index)

        if use_index == new_row_index:
            row = {**key_columns}
            table.append(row)

        return table[use_index]

    def _integrate_table_row(
        self,
        table_row: TableRow,
    ) -> None:
        leg_path = ".".join(table_row.path) + ":"
        row_key = self._make_row_key(table_row.key_columns)

        self._get_row(leg_path, "inventory", row_key,
                      table_row.key_columns).update(table_row.inventory_columns)

        self._get_row(leg_path, "status_data", row_key,
                      table_row.key_columns).update(table_row.status_columns)


#.
#   .--Inventory Tree------------------------------------------------------.
#   |  ___                      _                     _____                |
#   | |_ _|_ ____   _____ _ __ | |_ ___  _ __ _   _  |_   _| __ ___  ___   |
#   |  | || '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |   | || '__/ _ \/ _ \  |
#   |  | || | | \ V /  __/ | | | || (_) | |  | |_| |   | || | |  __/  __/  |
#   | |___|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |   |_||_|  \___|\___|  |
#   |                                         |___/                        |
#   +----------------------------------------------------------------------+
#   | Managing the inventory tree of a host                                |
#   '----------------------------------------------------------------------'


def _save_inventory_tree(hostname: HostName,
                         inventory_tree: StructuredDataTree) -> Optional[StructuredDataTree]:
    store.makedirs(cmk.utils.paths.inventory_output_dir)

    filepath = cmk.utils.paths.inventory_output_dir + "/" + hostname
    if inventory_tree.is_empty():
        # Remove empty inventory files. Important for host inventory icon
        if os.path.exists(filepath):
            os.remove(filepath)
        if os.path.exists(filepath + ".gz"):
            os.remove(filepath + ".gz")
        return None

    old_tree = StructuredDataTree().load_from(filepath)
    old_tree.normalize_nodes()
    if old_tree.is_equal(inventory_tree):
        console.verbose("Inventory was unchanged\n")
        return None

    if old_tree.is_empty():
        console.verbose("New inventory tree\n")
    else:
        console.verbose("Inventory tree has changed\n")
        old_time = os.stat(filepath).st_mtime
        arcdir = "%s/%s" % (cmk.utils.paths.inventory_archive_dir, hostname)
        store.makedirs(arcdir)
        os.rename(filepath, arcdir + ("/%d" % old_time))
    inventory_tree.save_to(cmk.utils.paths.inventory_output_dir, hostname)
    return old_tree


def _save_status_data_tree(hostname: HostName, status_data_tree: StructuredDataTree) -> None:
    if status_data_tree and not status_data_tree.is_empty():
        store.makedirs(cmk.utils.paths.status_data_dir)
        status_data_tree.save_to(cmk.utils.paths.status_data_dir, hostname)


def _run_inventory_export_hooks(host_config: config.HostConfig,
                                inventory_tree: StructuredDataTree) -> None:
    import cmk.base.inventory_plugins as inventory_plugins  # pylint: disable=import-outside-toplevel
    hooks = host_config.inventory_export_hooks

    if not hooks:
        return

    section.section_step("Execute inventory export hooks")
    for hookname, params in hooks:
        console.verbose("Execute export hook: %s%s%s%s" %
                        (tty.blue, tty.bold, hookname, tty.normal))
        try:
            func = inventory_plugins.inv_export[hookname]["export_function"]
            func(host_config.hostname, params, inventory_tree.get_raw_tree())
        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            raise MKGeneralException("Failed to execute export hook %s: %s" % (hookname, e))
