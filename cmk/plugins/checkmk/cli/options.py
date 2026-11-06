#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import dataclasses
from collections.abc import Mapping, Sequence
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
from cmk.cli.engine.readers import option_string as cli_option_string
from cmk.cli.internal import Option as CLIOption
from cmk.cli.internal import Value as CLIValue
from cmk.utils.check_utils import maincheckify


def parse_snmp_backend(backend: object) -> SNMPBackendEnum | None:
    match backend:
        case None:
            return None
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


def handle_fetcher_options(
    options: Mapping[str, object], *, defaults: FileCacheOptions | None = None
) -> FileCacheOptions:
    file_cache_options = defaults or FileCacheOptions()

    if options.get("cache", False):
        file_cache_options = dataclasses.replace(
            file_cache_options, disabled=False, use_outdated=True
        )

    if options.get("no-cache", False):
        file_cache_options = dataclasses.replace(
            file_cache_options, disabled=True, use_outdated=False
        )

    if options.get("no-tcp", False):
        file_cache_options = dataclasses.replace(
            file_cache_options, disabled=False, use_outdated=True, use_only_cache=True
        )

    return file_cache_options


FETCHER_OPTIONS: Final = [
    CLIOption(
        long="cache",
        help="Read info from data source cache files when existent, even when it "
        "is outdated. Only contact the data sources when the cache file "
        "is absent",
    ),
    CLIOption(
        long="no-cache",
        help="Never use cached information",
    ),
    CLIOption(
        long="no-tcp",
        help="Only use cache files. Skip hosts without cache files.",
    ),
    CLIOption(
        long="usewalk",
        help="Use snmpwalk stored with --snmpwalk",
    ),
]


def _untyped_option(value: CLIValue[object]) -> CLIOption:
    return CLIOption(
        long=value.long,
        help=value.help,
        short=value.short,
        argument=value.placeholder,
        deprecated_names=value.deprecated_names,
    )


SNMP_BACKEND_VALUE: Final = CLIValue(
    long="snmp-backend",
    help="Override default SNMP backend",
    placeholder="inline|classic|stored-walk",
    parse=parse_snmp_backend,
)

SNMP_BACKEND_OPTION: Final = _untyped_option(SNMP_BACKEND_VALUE)

FAKE_DNS_VALUE: Final = CLIValue(
    long="fake-dns",
    help="Fake IP addresses of all hosts to be IP. This prevents DNS lookups.",
    placeholder="IP",
    parse=HostAddress,
)

FAKE_DNS_OPTION: Final = _untyped_option(FAKE_DNS_VALUE)


def fake_dns_address(options: Mapping[str, object]) -> HostAddress | None:
    raw_address = cli_option_string(options, FAKE_DNS_OPTION.long)
    return None if raw_address is None else host_address(raw_address)


def _convert_sections_argument(arg: str) -> set[SectionName]:
    return {SectionName(n) for n in arg.split(",") if n}


option_sections = CLIOption(
    long="detect-sections",
    help=(
        "Comma separated list of sections. The provided sections (but no more) will be"
        " available (skipping SNMP detection)"
    ),
    argument="S",
    parse=_convert_sections_argument,
)


def get_plugins_option[TName: (str, CheckPluginName, InventoryPluginName, SectionName)](
    type_: type[TName],
) -> CLIOption:
    def _convert_plugins_argument(arg: str) -> set[TName]:
        return {type_(n) for n in arg.split(",") if n}

    return CLIOption(
        long="plugins",
        help="Restrict discovery, checking or inventory to these plugins",
        argument="P",
        parse=_convert_plugins_argument,
    )


def _convert_detect_plugins_argument(arg: str) -> set[str]:
    return {maincheckify(n) for n in arg.split(",") if n}


option_detect_plugins = CLIOption(
    long="detect-plugins",
    deprecated_names=frozenset({"checks"}),
    help="Same as '--plugins', but implies a best efford guess for --detect-sections",
    argument="P",
    parse=_convert_detect_plugins_argument,
)
