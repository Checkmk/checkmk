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
from cmk.base.agent_based.data_provider import ParsedSectionsBroker
from cmk.base.agent_based.utils import check_parsing_errors
from cmk.base.config import HostConfig

from ._inventory import (
    fetch_real_host_data,
    FetchedDataResult,
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

    if host_config.is_cluster:
        fetched_data_result = FetchedDataResult(
            parsed_sections_broker=ParsedSectionsBroker({}),
            source_results=(),
            parsing_errors=(),
            processing_failed=False,
        )
        trees = inventorize_cluster(host_config=host_config)
    else:
        fetched_data_result = fetch_real_host_data(
            host_config=host_config,
            selected_sections=selected_sections,
        )
        trees = inventorize_real_host(
            host_config=host_config,
            parsed_sections_broker=fetched_data_result.parsed_sections_broker,
            run_plugin_names=run_plugin_names,
        ).trees

    for subresult in check_parsing_errors(errors=fetched_data_result.parsing_errors):
        for line in subresult.details:
            console.warning(line)

    # TODO: fetched_data_results.source_results is completely ignored here.
    # We should process the results to make errors visible on the console
    count_i = trees.inventory.count_entries()
    count_s = trees.status_data.count_entries()
    section.section_success(f"Found {count_i} inventory entries")
    section.section_success(f"Found {count_s} status entries")
