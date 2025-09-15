#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, MutableMapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    Service,
    State,
)
from cmk.plugins.lib.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_PARAMS
from cmk.plugins.proxmox_ve.lib.node_filesystems import SectionNodeFilesystems


def discover_proxmox_ve_node_directory_filesystem(
    section: SectionNodeFilesystems,
) -> DiscoveryResult:
    yield from (Service(item=dir_filesystem) for dir_filesystem in section.directory_filesystems)


def _check_proxmox_ve_node_directory_filesystem(
    item: str,
    params: Mapping[str, Any],
    section: SectionNodeFilesystems,
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    if (filesystem := section.directory_filesystems.get(item)) is None:
        return

    yield from df_check_filesystem_single(
        value_store=value_store,
        mountpoint=item,
        filesystem_size=filesystem.maxdisk / (1024 * 1024),
        free_space=(filesystem.maxdisk - filesystem.disk) / (1024 * 1024),
        reserved_space=0.0,
        inodes_avail=None,
        inodes_total=None,
        params=params,
    )
    yield Result(state=State.OK, summary=f"Type: {filesystem.storage_type}")


def check_proxmox_ve_node_directory_filesystem(
    item: str, params: Mapping[str, Any], section: SectionNodeFilesystems
) -> CheckResult:
    yield from _check_proxmox_ve_node_directory_filesystem(
        item=item,
        params=params,
        section=section,
        value_store=get_value_store(),
    )


check_plugin_proxmox_ve_node_directory_filesystem = CheckPlugin(
    name="proxmox_ve_node_directory_filesystems",
    sections=["proxmox_ve_node_filesystems"],
    service_name="Filesystem %s",
    discovery_function=discover_proxmox_ve_node_directory_filesystem,
    check_function=check_proxmox_ve_node_directory_filesystem,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
