#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The HW/SW inventory commands: --inventory and --inventorize-marked-hosts."""

import dataclasses
from collections.abc import Sequence
from typing import Final

from cmk.ccc.hostaddress import HostAddress
from cmk.checkengine.plugins import InventoryPluginName
from cmk.checkengine.snmplib import SNMPBackendEnum
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import Reader as CLIReader

from .options import (
    FAKE_DNS_VALUE,
    file_cache_request,
    FileCacheRequest,
    INVENTORY_PLUGINS_VALUE,
    plugin_selection_request,
    PluginSelectionRequest,
    SNMP_BACKEND_VALUE,
    USEWALK_FLAG,
)

_FORCE_FLAG: Final = CLIFlag(
    long="force",
    short="f",
    help="Use cached agent data even if it's outdated.",
)


@dataclasses.dataclass(frozen=True, kw_only=True)
class InventoryRequest:
    file_cache: FileCacheRequest
    usewalk: bool
    snmp_backend: SNMPBackendEnum | None
    force: bool
    plugin_selection: PluginSelectionRequest[InventoryPluginName]
    fake_dns: HostAddress | None
    hosts: Sequence[str]


def _inventory_request(options: CLIReader) -> InventoryRequest:
    return InventoryRequest(
        file_cache=file_cache_request(options),
        usewalk=options.flag(USEWALK_FLAG),
        snmp_backend=options.value(SNMP_BACKEND_VALUE),
        force=options.flag(_FORCE_FLAG),
        plugin_selection=plugin_selection_request(options, INVENTORY_PLUGINS_VALUE),
        fake_dns=options.value(FAKE_DNS_VALUE),
        hosts=options.arguments(CLIArguments(placeholder="HOST1 HOST2...", parse=str)),
    )


cli_command_inventory = CLICommand(
    name="inventory",
    handler="cmk.plugins.checkmk.cli.handlers.inventory:cli_handler_inventory",
    long="inventory",
    short="i",
    request=_inventory_request,
    help="Do a HW/SW Inventory on some or all hosts",
    description=[
        (
            "Does a HW/SW Inventory for all, one or several "
            "hosts. If you add the option -f, --force then persisted sections "
            "will be used even if they are outdated."
        )
    ],
)


@dataclasses.dataclass(frozen=True, kw_only=True)
class InventorizeMarkedHostsRequest:
    file_cache: FileCacheRequest
    usewalk: bool
    snmp_backend: SNMPBackendEnum | None
    fake_dns: HostAddress | None


def _inventorize_marked_hosts_request(options: CLIReader) -> InventorizeMarkedHostsRequest:
    return InventorizeMarkedHostsRequest(
        file_cache=file_cache_request(options),
        usewalk=options.flag(USEWALK_FLAG),
        snmp_backend=options.value(SNMP_BACKEND_VALUE),
        fake_dns=options.value(FAKE_DNS_VALUE),
    )


cli_command_inventorize_marked_hosts = CLICommand(
    name="inventorize_marked_hosts",
    handler="cmk.plugins.checkmk.cli.handlers.inventory:cli_handler_inventorize_marked_hosts",
    long="inventorize-marked-hosts",
    request=_inventorize_marked_hosts_request,
    help="Run inventory for hosts which previously had no tree data",
    description=[
        "Run actual service HW/SW Inventory on all hosts that had no tree data",
        "in the previous run",
    ],
)
