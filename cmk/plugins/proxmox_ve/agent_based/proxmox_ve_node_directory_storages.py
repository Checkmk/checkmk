#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
)
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS
from cmk.plugins.proxmox_ve.lib.node_storages import (
    check_proxmox_ve_node_storage,
    SectionNodeStorages,
)


def discover_proxmox_ve_node_directory_storage(
    section: SectionNodeStorages,
) -> DiscoveryResult:
    yield from (Service(item=dir_storage) for dir_storage in section.directory_storages)


def check_proxmox_ve_node_directory_storage(
    item: str,
    params: Mapping[str, object],
    section: SectionNodeStorages,
) -> CheckResult:
    yield from check_proxmox_ve_node_storage(
        item=item,
        params=params,
        section=section.directory_storages,
        value_store=get_value_store(),
    )


check_plugin_proxmox_ve_node_directory_storage = CheckPlugin(
    name="proxmox_ve_node_directory_storages",
    sections=["proxmox_ve_node_storage"],
    service_name="Proxmox VE Storage %s",
    discovery_function=discover_proxmox_ve_node_directory_storage,
    check_function=check_proxmox_ve_node_directory_storage,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
