#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Container

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.check_utils import ActiveCheckResult
from cmk.utils.structured_data import TreeOrArchiveStore
from cmk.utils.type_defs import EVERYTHING, HostName, InventoryPluginName

from cmk.core_helpers.type_defs import SectionNameCollection

import cmk.base.config as config
import cmk.base.section as section
from cmk.base.agent_based.utils import check_parsing_errors, summarize_host_sections
from cmk.base.config import HostConfig

from ._inventory import (
    check_trees,
    fetch_real_host_data,
    inventorize_cluster,
    inventorize_real_host,
)

__all__ = ["commandline_inventory"]


def commandline_inventory(
    hostnames: list[HostName],
    *,
    selected_sections: SectionNameCollection,
    run_plugin_names: Container[InventoryPluginName] = EVERYTHING,
) -> None:
    store.makedirs(cmk.utils.paths.inventory_output_dir)
    store.makedirs(cmk.utils.paths.inventory_archive_dir)

    for hostname in hostnames:
        section.section_begin(hostname)
        host_config = HostConfig.make_host_config(hostname)
        try:
            _commandline_inventory_on_host(
                host_config=host_config,
                selected_sections=selected_sections,
                run_plugin_names=run_plugin_names,
            )

        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            section.section_error("%s" % e)
        finally:
            cmk.utils.cleanup.cleanup_globals()


def _commandline_inventory_on_host(
    *,
    host_config: HostConfig,
    run_plugin_names: Container[InventoryPluginName],
    selected_sections: SectionNameCollection,
) -> None:
    section.section_step("Inventorizing")
    parameters = host_config.hwsw_inventory_parameters

    tree_or_archive_store = TreeOrArchiveStore(
        cmk.utils.paths.inventory_output_dir,
        cmk.utils.paths.inventory_archive_dir,
    )
    old_tree = tree_or_archive_store.load(host_name=host_config.hostname)

    if host_config.is_cluster:
        tree_aggregator = inventorize_cluster(host_config=host_config)
        _show_result(
            ActiveCheckResult.from_subresults(
                *check_trees(
                    parameters=parameters,
                    inventory_tree=tree_aggregator.trees.inventory,
                    status_data_tree=tree_aggregator.trees.status_data,
                    old_tree=old_tree,
                ),
            )
        )
        return

    fetched_data_result = fetch_real_host_data(
        host_config=host_config,
        selected_sections=selected_sections,
    )
    tree_aggregator = inventorize_real_host(
        host_config=host_config,
        parsed_sections_broker=fetched_data_result.parsed_sections_broker,
        run_plugin_names=run_plugin_names,
    )

    if fetched_data_result.processing_failed:
        active_check_result = ActiveCheckResult(parameters.fail_status, "Cannot update tree")
    else:
        active_check_result = ActiveCheckResult()

    _show_result(
        ActiveCheckResult.from_subresults(
            active_check_result,
            *check_trees(
                parameters=parameters,
                inventory_tree=tree_aggregator.trees.inventory,
                status_data_tree=tree_aggregator.trees.status_data,
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
        )
    )


def _show_result(result: ActiveCheckResult) -> None:
    if result.state:
        section.section_error(result.summary)
    else:
        section.section_success(result.summary)
