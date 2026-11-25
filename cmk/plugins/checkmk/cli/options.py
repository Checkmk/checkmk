#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import dataclasses
from collections.abc import Callable
from typing import Final

from cmk.ccc.hostaddress import HostAddress
from cmk.checkengine.plugins import (
    CheckPluginName,
    InventoryPluginName,
    SectionName,
)
from cmk.checkengine.snmplib import (
    SNMPBackendEnum,
)
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import Reader as CLIReader
from cmk.cli.internal import Value as CLIValue
from cmk.utils.check_utils import maincheckify


def _parse_snmp_backend(backend: str) -> SNMPBackendEnum:
    match backend:
        case "inline":
            return SNMPBackendEnum.INLINE
        case "classic":
            return SNMPBackendEnum.CLASSIC
        case "stored-walk":
            return SNMPBackendEnum.STORED_WALK
        case _:
            raise ValueError(backend)


@dataclasses.dataclass(frozen=True, kw_only=True)
class FileCacheRequest:
    cache: bool
    no_cache: bool
    no_tcp: bool


_CACHE_FLAG: Final = CLIFlag(
    long="cache",
    help="Read info from data source cache files when existent, even when it "
    "is outdated. Only contact the data sources when the cache file "
    "is absent",
)

_NO_CACHE_FLAG: Final = CLIFlag(
    long="no-cache",
    help="Never use cached information",
)

_NO_TCP_FLAG: Final = CLIFlag(
    long="no-tcp",
    help="Only use cache files. Skip hosts without cache files.",
)

_USEWALK_FLAG: Final = CLIFlag(
    long="usewalk",
    help="Use snmpwalk stored with --snmpwalk",
)


def file_cache_request(options: CLIReader) -> FileCacheRequest:
    return FileCacheRequest(
        cache=options.flag(_CACHE_FLAG),
        no_cache=options.flag(_NO_CACHE_FLAG),
        no_tcp=options.flag(_NO_TCP_FLAG),
    )


SNMP_BACKEND_VALUE: Final = CLIValue(
    long="snmp-backend",
    help="Override default SNMP backend",
    placeholder="inline|classic|stored-walk",
    parse=_parse_snmp_backend,
)

FAKE_DNS_VALUE: Final = CLIValue(
    long="fake-dns",
    help="Fake IP addresses of all hosts to be IP. This prevents DNS lookups.",
    placeholder="IP",
    parse=HostAddress,
)


@dataclasses.dataclass(frozen=True, kw_only=True)
class FetchRequest:
    file_cache: FileCacheRequest
    usewalk: bool
    snmp_backend: SNMPBackendEnum | None
    fake_dns: HostAddress | None


def fetch_request(options: CLIReader) -> FetchRequest:
    return FetchRequest(
        file_cache=file_cache_request(options),
        usewalk=options.flag(_USEWALK_FLAG),
        snmp_backend=options.value(SNMP_BACKEND_VALUE),
        fake_dns=options.value(FAKE_DNS_VALUE),
    )


def fake_dns_request(options: CLIReader) -> HostAddress | None:
    return options.value(FAKE_DNS_VALUE)


def _comma_separated[T](parse: Callable[[str], T]) -> Callable[[str], frozenset[T]]:
    def parse_each(argument: str) -> frozenset[T]:
        return frozenset(parse(name) for name in argument.split(",") if name)

    return parse_each


_DETECT_SECTIONS_VALUE: Final = CLIValue(
    long="detect-sections",
    help=(
        "Comma separated list of sections. The provided sections (but no more) will be"
        " available (skipping SNMP detection)"
    ),
    placeholder="S",
    parse=_comma_separated(SectionName),
)


def _plugins_value[PluginName: (CheckPluginName, InventoryPluginName)](
    plugin_name: type[PluginName],
) -> CLIValue[frozenset[PluginName]]:
    return CLIValue(
        long="plugins",
        help="Restrict discovery, checking or inventory to these plugins",
        placeholder="P",
        parse=_comma_separated(plugin_name),
    )


CHECK_PLUGINS_VALUE: Final = _plugins_value(CheckPluginName)

INVENTORY_PLUGINS_VALUE: Final = _plugins_value(InventoryPluginName)


_DETECT_PLUGINS_VALUE: Final = CLIValue(
    long="detect-plugins",
    deprecated_names=frozenset({"checks"}),
    help="Same as '--plugins', but implies a best efford guess for --detect-sections",
    placeholder="P",
    parse=_comma_separated(maincheckify),
)


@dataclasses.dataclass(frozen=True, kw_only=True)
class PluginSelectionRequest[PluginName]:
    detect_sections: frozenset[SectionName] | None
    plugins: frozenset[PluginName] | None
    detect_plugins: frozenset[str] | None


def plugin_selection_request[PluginName: (CheckPluginName, InventoryPluginName)](
    options: CLIReader, plugins: CLIValue[frozenset[PluginName]]
) -> PluginSelectionRequest[PluginName]:
    return PluginSelectionRequest(
        detect_sections=options.value(_DETECT_SECTIONS_VALUE),
        plugins=options.value(plugins),
        detect_plugins=options.value(_DETECT_PLUGINS_VALUE),
    )
