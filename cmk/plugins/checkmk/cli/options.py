#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import dataclasses
from collections.abc import Sequence
from typing import Final

from cmk.ccc.exceptions import MKBailOut
from cmk.ccc.hostaddress import HostAddress, HostNameValidationError
from cmk.checkengine.filecache import FileCacheOptions
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


def parse_snmp_backend(backend: str) -> SNMPBackendEnum:
    match backend:
        case "inline":
            return SNMPBackendEnum.INLINE
        case "classic":
            return SNMPBackendEnum.CLASSIC
        case "stored-walk":
            return SNMPBackendEnum.STORED_WALK
        case _:
            raise ValueError(backend)


def host_address(raw_host_address: str) -> HostAddress:
    try:
        return HostAddress(raw_host_address)
    except HostNameValidationError as exc:
        raise MKBailOut(str(exc)) from exc


def host_addresses(raw_host_addresses: Sequence[str]) -> Sequence[HostAddress]:
    return [host_address(raw_host_address) for raw_host_address in raw_host_addresses]


@dataclasses.dataclass(frozen=True, kw_only=True)
class FileCacheRequest:
    cache: bool
    no_cache: bool
    no_tcp: bool


def make_file_cache_options(
    request: FileCacheRequest, *, defaults: FileCacheOptions | None = None
) -> FileCacheOptions:
    file_cache_options = defaults or FileCacheOptions()

    if request.cache:
        file_cache_options = dataclasses.replace(
            file_cache_options, disabled=False, use_outdated=True
        )

    if request.no_cache:
        file_cache_options = dataclasses.replace(
            file_cache_options, disabled=True, use_outdated=False
        )

    if request.no_tcp:
        file_cache_options = dataclasses.replace(
            file_cache_options, disabled=False, use_outdated=True, use_only_cache=True
        )

    return file_cache_options


CACHE_FLAG: Final = CLIFlag(
    long="cache",
    help="Read info from data source cache files when existent, even when it "
    "is outdated. Only contact the data sources when the cache file "
    "is absent",
)

NO_CACHE_FLAG: Final = CLIFlag(
    long="no-cache",
    help="Never use cached information",
)

NO_TCP_FLAG: Final = CLIFlag(
    long="no-tcp",
    help="Only use cache files. Skip hosts without cache files.",
)

USEWALK_FLAG: Final = CLIFlag(
    long="usewalk",
    help="Use snmpwalk stored with --snmpwalk",
)


def file_cache_request(options: CLIReader) -> FileCacheRequest:
    return FileCacheRequest(
        cache=options.flag(CACHE_FLAG),
        no_cache=options.flag(NO_CACHE_FLAG),
        no_tcp=options.flag(NO_TCP_FLAG),
    )


SNMP_BACKEND_VALUE: Final = CLIValue(
    long="snmp-backend",
    help="Override default SNMP backend",
    placeholder="inline|classic|stored-walk",
    parse=parse_snmp_backend,
)

FAKE_DNS_VALUE: Final = CLIValue(
    long="fake-dns",
    help="Fake IP addresses of all hosts to be IP. This prevents DNS lookups.",
    placeholder="IP",
    parse=HostAddress,
)


def fake_dns_request(options: CLIReader) -> HostAddress | None:
    return options.value(FAKE_DNS_VALUE)


def _parse_sections(argument: str) -> frozenset[SectionName]:
    return frozenset(SectionName(n) for n in argument.split(",") if n)


DETECT_SECTIONS_VALUE: Final = CLIValue(
    long="detect-sections",
    help=(
        "Comma separated list of sections. The provided sections (but no more) will be"
        " available (skipping SNMP detection)"
    ),
    placeholder="S",
    parse=_parse_sections,
)


def plugins_value[TName: (str, CheckPluginName, InventoryPluginName, SectionName)](
    type_: type[TName],
) -> CLIValue[frozenset[TName]]:
    def _parse_plugins(argument: str) -> frozenset[TName]:
        return frozenset(type_(n) for n in argument.split(",") if n)

    return CLIValue(
        long="plugins",
        help="Restrict discovery, checking or inventory to these plugins",
        placeholder="P",
        parse=_parse_plugins,
    )


def _parse_detect_plugins(argument: str) -> frozenset[str]:
    return frozenset(maincheckify(n) for n in argument.split(",") if n)


DETECT_PLUGINS_VALUE: Final = CLIValue(
    long="detect-plugins",
    deprecated_names=frozenset({"checks"}),
    help="Same as '--plugins', but implies a best efford guess for --detect-sections",
    placeholder="P",
    parse=_parse_detect_plugins,
)


@dataclasses.dataclass(frozen=True, kw_only=True)
class PluginSelectionRequest[PluginName]:
    detect_sections: frozenset[SectionName] | None
    plugins: frozenset[PluginName] | None
    detect_plugins: frozenset[str] | None


def plugin_selection_request[PluginName: (CheckPluginName, InventoryPluginName)](
    options: CLIReader, type_: type[PluginName]
) -> PluginSelectionRequest[PluginName]:
    return PluginSelectionRequest(
        detect_sections=options.value(DETECT_SECTIONS_VALUE),
        plugins=options.value(plugins_value(type_)),
        detect_plugins=options.value(DETECT_PLUGINS_VALUE),
    )
