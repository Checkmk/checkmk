#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Container, Mapping
from pathlib import Path

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.paths
from cmk.utils.log import section
from cmk.utils.structured_data import load_tree, RawIntervalsFromConfig
from cmk.utils.type_defs import EVERYTHING, HostName, SectionName

from cmk.checkers import (
    FetcherFunction,
    InventoryPlugin,
    ParserFunction,
    SectionPlugin,
    SummarizerFunction,
)
from cmk.checkers.inventory import HWSWInventoryParameters, InventoryPluginName

from cmk.base.config import ConfigCache

from ._inventory import inventorize_cluster, inventorize_host

__all__ = ["commandline_inventory"]


def commandline_inventory(
    hostname: HostName,
    *,
    config_cache: ConfigCache,
    fetcher: FetcherFunction,
    parser: ParserFunction,
    summarizer: SummarizerFunction,
    parameters: HWSWInventoryParameters,
    raw_intervals_from_config: RawIntervalsFromConfig,
    section_plugins: Mapping[SectionName, SectionPlugin],
    inventory_plugins: Mapping[InventoryPluginName, InventoryPlugin],
    run_plugin_names: Container[InventoryPluginName] = EVERYTHING,
) -> None:
    section.section_begin(hostname)
    section.section_step("Inventorizing")
    try:
        old_tree = load_tree(Path(cmk.utils.paths.inventory_output_dir, hostname))
        if config_cache.is_cluster(hostname):
            check_result = inventorize_cluster(
                config_cache.nodes_of(hostname) or (),
                parameters=parameters,
                old_tree=old_tree,
            ).check_result
        else:
            check_result = inventorize_host(
                hostname,
                fetcher=fetcher,
                parser=parser,
                summarizer=summarizer,
                inventory_parameters=config_cache.inventory_parameters,
                section_plugins=section_plugins,
                inventory_plugins=inventory_plugins,
                run_plugin_names=run_plugin_names,
                parameters=parameters,
                raw_intervals_from_config=raw_intervals_from_config,
                old_tree=old_tree,
            ).check_result
        if check_result.state:
            section.section_error(check_result.summary)
        else:
            section.section_success(check_result.summary)

    except Exception as e:
        if cmk.utils.debug.enabled():
            raise
        section.section_error("%s" % e)
    finally:
        cmk.utils.cleanup.cleanup_globals()
