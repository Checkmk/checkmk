#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Container
from pathlib import Path
from typing import Callable

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.structured_data import load_tree
from cmk.utils.type_defs import EVERYTHING, HostName, InventoryPluginName, RuleSetName

from cmk.core_helpers.type_defs import SectionNameCollection

import cmk.base.section as section
from cmk.base.config import get_config_cache, HWSWInventoryParameters

from ._inventory import check_inventory_tree

__all__ = ["commandline_inventory"]


def commandline_inventory(
    hostnames: list[HostName],
    *,
    selected_sections: SectionNameCollection,
    run_plugin_names: Container[InventoryPluginName] = EVERYTHING,
) -> None:
    store.makedirs(cmk.utils.paths.inventory_output_dir)
    store.makedirs(cmk.utils.paths.inventory_archive_dir)

    config_cache = get_config_cache()
    for hostname in hostnames:
        section.section_begin(hostname)
        try:
            _commandline_inventory_on_host(
                hostname,
                inventory_parameters=config_cache.inventory_parameters,
                parameters=config_cache.hwsw_inventory_parameters(hostname),
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
    host_name: HostName,
    *,
    inventory_parameters: Callable[[HostName, RuleSetName], dict[str, object]],
    parameters: HWSWInventoryParameters,
    selected_sections: SectionNameCollection,
    run_plugin_names: Container[InventoryPluginName],
) -> None:
    section.section_step("Inventorizing")

    old_tree = load_tree(Path(cmk.utils.paths.inventory_output_dir, host_name))

    check_result = check_inventory_tree(
        host_name,
        inventory_parameters=inventory_parameters,
        selected_sections=selected_sections,
        run_plugin_names=run_plugin_names,
        parameters=parameters,
        old_tree=old_tree,
    ).check_result

    if check_result.state:
        section.section_error(check_result.summary)
    else:
        section.section_success(check_result.summary)
