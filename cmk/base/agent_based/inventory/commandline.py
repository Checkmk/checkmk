#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Container

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.structured_data import load_tree
from cmk.utils.type_defs import EVERYTHING, HostName, InventoryPluginName

from cmk.core_helpers.type_defs import SectionNameCollection

import cmk.base.section as section
from cmk.base.config import HostConfig

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
    selected_sections: SectionNameCollection,
    run_plugin_names: Container[InventoryPluginName],
) -> None:
    section.section_step("Inventorizing")

    old_tree = load_tree(Path(cmk.utils.paths.inventory_output_dir, host_config.hostname))

    check_result = check_inventory_tree(
        host_config=host_config,
        selected_sections=selected_sections,
        run_plugin_names=run_plugin_names,
        parameters=host_config.hwsw_inventory_parameters,
        old_tree=old_tree,
    ).check_result

    if check_result.state:
        section.section_error(check_result.summary)
    else:
        section.section_success(check_result.summary)
