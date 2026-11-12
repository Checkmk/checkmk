#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The service discovery commands: --check-discovery and --discover."""

from dataclasses import dataclass
from typing import Final

from cmk.ccc.hostaddress import HostAddress
from cmk.checkengine.plugins import CheckPluginName
from cmk.checkengine.snmplib import SNMPBackendEnum
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Count as CLICount
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import Reader as CLIReader

from .options import (
    CHECK_PLUGINS_VALUE,
    FAKE_DNS_VALUE,
    file_cache_request,
    FileCacheRequest,
    plugin_selection_request,
    PluginSelectionRequest,
    SNMP_BACKEND_VALUE,
    USEWALK_FLAG,
)


@dataclass(frozen=True, kw_only=True)
class CheckDiscoveryRequest:
    file_cache: FileCacheRequest
    usewalk: bool
    snmp_backend: SNMPBackendEnum | None
    fake_dns: HostAddress | None


def _check_discovery_request(options: CLIReader) -> CheckDiscoveryRequest:
    return CheckDiscoveryRequest(
        file_cache=file_cache_request(options),
        usewalk=options.flag(USEWALK_FLAG),
        snmp_backend=options.value(SNMP_BACKEND_VALUE),
        fake_dns=options.value(FAKE_DNS_VALUE),
    )


cli_command_check_discovery = CLICommand(
    name="check_discovery",
    handler="cmk.plugins.checkmk.cli.handlers.discovery:cli_handler_check_discovery",
    long="check-discovery",
    request=_check_discovery_request,
    arguments=CLIArguments("HOSTNAME"),
    help="Check for not yet monitored services",
    description=[
        (
            "Make Check_MK behave as monitoring plug-ins that checks if an "
            "inventory would find new or vanished services for the host. "
            "If configured to do so, this will queue those hosts for automatic "
            "autodiscovery"
        )
    ],
)


_DISCOVER_COUNT: Final = CLICount(
    long="discover",
    short="I",
    help="Delete existing services before starting discovery",
)


_ONLY_HOST_LABELS_FLAG: Final = CLIFlag(
    long="only-host-labels",
    short="L",
    help="Restrict discovery to host labels only",
)


@dataclass(frozen=True, kw_only=True)
class DiscoverRequest:
    file_cache: FileCacheRequest
    usewalk: bool
    snmp_backend: SNMPBackendEnum | None
    discover: int
    plugin_selection: PluginSelectionRequest[CheckPluginName]
    only_host_labels: bool
    fake_dns: HostAddress | None


def _discover_request(options: CLIReader) -> DiscoverRequest:
    return DiscoverRequest(
        file_cache=file_cache_request(options),
        usewalk=options.flag(USEWALK_FLAG),
        snmp_backend=options.value(SNMP_BACKEND_VALUE),
        discover=options.count(_DISCOVER_COUNT),
        plugin_selection=plugin_selection_request(options, CHECK_PLUGINS_VALUE),
        only_host_labels=options.flag(_ONLY_HOST_LABELS_FLAG),
        fake_dns=options.value(FAKE_DNS_VALUE),
    )


cli_command_discover = CLICommand(
    name="discover",
    handler="cmk.plugins.checkmk.cli.handlers.discovery:cli_handler_discover",
    long="discover",
    short="I",
    request=_discover_request,
    arguments=CLIArguments("[-I] HOST1 HOST2...", optional=True),
    help="Find new services",
    description=[
        (
            "Make Check_MK behave as monitoring plug-ins that checks if an "
            "inventory would find new or vanished services for the host. "
            "If configured to do so, this will queue those hosts for automatic "
            "autodiscovery"
        ),
        (
            "Can be restricted to certain check types. Write '--checks df -I' if "
            "you just want to look for new filesystems. Use 'cmk -L' for a "
            "list of all check types."
        ),
        (
            "Can also be restricted to only discovering new host labels. "
            "Use: '--only-host-labels' or '-L' "
        ),
        "-II does the same as -I but deletes all existing checks of the specified types and hosts.",
        (
            "Exits with 1 if the discovery failed for at least one host, or if one of "
            "a host's data sources could not be contacted. For such a host, -II "
            "behaves like -I: it adds what the other data sources found, but neither "
            "removes nor changes existing services and host labels. The discovery of "
            "the remaining hosts is carried out regardless."
        ),
    ],
)
