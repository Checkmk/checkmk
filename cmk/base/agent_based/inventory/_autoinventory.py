#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.log import console
from cmk.utils.type_defs import EVERYTHING

from cmk.core_helpers.cache import FileCacheOptions

import cmk.base.config as config
from cmk.base.auto_queue import AutoQueue, get_up_hosts, TimeLimitFilter

from .active import execute_active_check_inventory

__all__ = ["inventorize_marked_hosts"]


def inventorize_marked_hosts(
    config_cache: config.ConfigCache,
    autoinventory_queue: AutoQueue,
    *,
    file_cache_options: FileCacheOptions,
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
                    file_cache_options=file_cache_options,
                    inventory_parameters=config_cache.inventory_parameters,
                    parameters=config_cache.hwsw_inventory_parameters(host_name),
                )
