#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping

from cmk.utils.auto_queue import AutoQueue, get_up_hosts, TimeLimitFilter
from cmk.utils.log import console
from cmk.utils.type_defs import EVERYTHING, HostName, SectionName

from cmk.checkers import (
    FetcherFunction,
    InventoryPlugin,
    ParserFunction,
    PSectionPlugin,
    SummarizerFunction,
)
from cmk.checkers.inventory import InventoryPluginName

from cmk.base.config import ConfigCache

from ._active import execute_active_check_inventory

__all__ = ["inventorize_marked_hosts"]


def inventorize_marked_hosts(
    config_cache: ConfigCache,
    autoinventory_queue: AutoQueue,
    *,
    parser: ParserFunction,
    fetcher: FetcherFunction,
    summarizer: Callable[[HostName], SummarizerFunction],
    section_plugins: Mapping[SectionName, PSectionPlugin],
    inventory_plugins: Mapping[InventoryPluginName, InventoryPlugin],
) -> None:
    autoinventory_queue.cleanup(
        valid_hosts=config_cache.all_configured_hosts(),
        logger=console.verbose,
    )

    if autoinventory_queue.oldest() is None:
        console.verbose("Autoinventory: No hosts marked by inventory check\n")
        return

    console.verbose("Autoinventory: Inventorize all hosts marked by inventory check:\n")
    process_hosts = EVERYTHING if (up_hosts := get_up_hosts()) is None else up_hosts

    with TimeLimitFilter(limit=120, grace=10, label="hosts") as time_limited:
        for host_name in time_limited(autoinventory_queue.queued_hosts()):
            if host_name in process_hosts:
                execute_active_check_inventory(
                    host_name,
                    config_cache=config_cache,
                    parser=parser,
                    fetcher=fetcher,
                    summarizer=summarizer(host_name),
                    section_plugins=section_plugins,
                    inventory_plugins=inventory_plugins,
                    inventory_parameters=config_cache.inventory_parameters,
                    parameters=config_cache.hwsw_inventory_parameters(host_name),
                    raw_intervals_from_config=config_cache.inv_retention_intervals(host_name),
                )
