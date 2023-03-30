#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Container, Mapping
from pathlib import Path
from typing import Callable

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.paths
from cmk.utils.log import section
from cmk.utils.structured_data import load_tree, RawIntervalsFromConfig
from cmk.utils.type_defs import (
    EVERYTHING,
    HostName,
    HWSWInventoryParameters,
    InventoryPluginName,
    SectionName,
)

from cmk.checkers import (
    FetcherFunction,
    ParserFunction,
    PInventoryPlugin,
    PSectionPlugin,
    SummarizerFunction,
)

from cmk.base.config import ConfigCache

from ._inventory import check_inventory_tree

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
    section_plugins: Mapping[SectionName, PSectionPlugin],
    inventory_plugins: Mapping[InventoryPluginName, PInventoryPlugin],
    run_plugin_names: Container[InventoryPluginName] = EVERYTHING,
) -> None:
    section.section_begin(hostname)
    try:
        _commandline_inventory_on_host(
            hostname,
            config_cache=config_cache,
            fetcher=fetcher,
            parser=parser,
            summarizer=summarizer,
            inventory_parameters=config_cache.inventory_parameters,
            parameters=parameters,
            raw_intervals_from_config=raw_intervals_from_config,
            section_plugins=section_plugins,
            inventory_plugins=inventory_plugins,
            run_plugin_names=run_plugin_names,
        )

    except Exception as e:
        if cmk.utils.debug.enabled():
            raise
        section.section_error("%s" % e)
    finally:
        cmk.utils.cleanup.cleanup_globals()


def _commandline_inventory_on_host(
    host_name: HostName,
    *,
    config_cache: ConfigCache,
    fetcher: FetcherFunction,
    parser: ParserFunction,
    summarizer: SummarizerFunction,
    inventory_parameters: Callable[[HostName, PInventoryPlugin], dict[str, object]],
    parameters: HWSWInventoryParameters,
    raw_intervals_from_config: RawIntervalsFromConfig,
    section_plugins: Mapping[SectionName, PSectionPlugin],
    inventory_plugins: Mapping[InventoryPluginName, PInventoryPlugin],
    run_plugin_names: Container[InventoryPluginName],
) -> None:
    section.section_step("Inventorizing")

    old_tree = load_tree(Path(cmk.utils.paths.inventory_output_dir, host_name))

    check_result = check_inventory_tree(
        host_name,
        config_cache=config_cache,
        fetcher=fetcher,
        parser=parser,
        summarizer=summarizer,
        inventory_parameters=inventory_parameters,
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
