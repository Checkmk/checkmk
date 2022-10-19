#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Container

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.log import console
from cmk.utils.type_defs import EVERYTHING, HostName, InventoryPluginName

from cmk.core_helpers.type_defs import SectionNameCollection

import cmk.base.section as section
from cmk.base.agent_based.utils import check_parsing_errors
from cmk.base.config import HostConfig

from ._inventory import inventorize_cluster, inventorize_real_host
from ._retentions import RetentionsTracker

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

    if host_config.is_cluster:
        inv_result = inventorize_cluster(host_config=host_config)
    else:
        inv_result = inventorize_real_host(
            host_config=host_config,
            selected_sections=selected_sections,
            run_plugin_names=run_plugin_names,
            retentions_tracker=RetentionsTracker(host_config.inv_retention_intervals),
        )

    for subresult in check_parsing_errors(errors=inv_result.parsing_errors):
        for line in subresult.details:
            console.warning(line)

    # TODO: inv_results.source_results is completely ignored here.
    # We should process the results to make errors visible on the console
    count_i = inv_result.trees.inventory.count_entries()
    count_s = inv_result.trees.status_data.count_entries()
    section.section_success(f"Found {count_i} inventory entries")
    section.section_success(f"Found {count_s} status entries")
