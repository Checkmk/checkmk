#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
)
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS
from cmk.plugins.proxmox_ve.lib.node_filesystems import (
    check_proxmox_ve_node_filesystems,
    SectionNodeFilesystems,
)


def discover_proxmox_ve_node_lvm_filesystem(
    section: SectionNodeFilesystems,
) -> DiscoveryResult:
    yield from (Service(item=lvm_filesystem) for lvm_filesystem in section.lvm_filesystems)


def check_proxmox_ve_node_lvm_filesystem(
    item: str, params: Mapping[str, Any], section: SectionNodeFilesystems
) -> CheckResult:
    yield from check_proxmox_ve_node_filesystems(
        item=item,
        params=params,
        section=section.lvm_filesystems,
        value_store=get_value_store(),
    )


check_plugin_proxmox_ve_node_lvm_filesystem = CheckPlugin(
    name="proxmox_ve_node_lvm_filesystems",
    sections=["proxmox_ve_node_filesystems"],
    service_name="Filesystem %s-lvm",
    discovery_function=discover_proxmox_ve_node_lvm_filesystem,
    check_function=check_proxmox_ve_node_lvm_filesystem,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
