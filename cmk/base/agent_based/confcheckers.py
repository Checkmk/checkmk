#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Concrete implementation of checkers functionality."""

from __future__ import annotations

import itertools
import logging
from collections.abc import Iterable, Iterator, Mapping, Sequence
from typing import Final

import cmk.utils.tty as tty
from cmk.utils.cpu_tracking import CPUTracker, Snapshot
from cmk.utils.exceptions import OnError
from cmk.utils.log import console
from cmk.utils.piggyback import PiggybackTimeSettings
from cmk.utils.type_defs import (
    AgentRawData,
    CheckPluginName,
    ExitSpec,
    HostAddress,
    HostName,
    InventoryPluginName,
    result,
    SectionName,
    ServiceState,
)

from cmk.snmplib.type_defs import SNMPRawData

from cmk.fetchers import Fetcher, get_raw_data, Mode
from cmk.fetchers.filecache import FileCache, FileCacheOptions, MaxAge

from cmk.checkers import (
    parse_raw_data,
    PCheckPlugin,
    PDiscoveryPlugin,
    PHostLabelDiscoveryPlugin,
    PInventoryPlugin,
    PSectionPlugin,
    Source,
    SourceInfo,
)
from cmk.checkers.checkresults import ActiveCheckResult
from cmk.checkers.host_sections import HostSections
from cmk.checkers.summarize import summarize
from cmk.checkers.type_defs import NO_SELECTION, SectionNameCollection

import cmk.base.api.agent_based.register._config as _api
import cmk.base.config as config
from cmk.base.config import ConfigCache
from cmk.base.sources import make_parser, make_sources

__all__ = [
    "CheckPluginMapper",
    "ConfiguredFetcher",
    "ConfiguredParser",
    "ConfiguredSummarizer",
    "DiscoveryPluginMapper",
    "HostLabelPluginMapper",
    "InventoryPluginMapper",
    "SectionPluginMapper",
]


def _fetch_all(
    sources: Iterable[Source], *, simulation: bool, file_cache_options: FileCacheOptions, mode: Mode
) -> Sequence[tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception], Snapshot]]:
    console.verbose("%s+%s %s\n", tty.yellow, tty.normal, "Fetching data".upper())
    return [
        _do_fetch(
            source.source_info(),
            source.file_cache(simulation=simulation, file_cache_options=file_cache_options),
            source.fetcher(),
            mode=mode,
        )
        for source in sources
    ]


def _do_fetch(
    source_info: SourceInfo,
    file_cache: FileCache,
    fetcher: Fetcher,
    *,
    mode: Mode,
) -> tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception], Snapshot]:
    console.vverbose(f"  Source: {source_info}\n")
    with CPUTracker() as tracker:
        raw_data = get_raw_data(file_cache, fetcher, mode)
    return source_info, raw_data, tracker.duration


class ConfiguredParser:
    def __init__(
        self,
        config_cache: ConfigCache,
        *,
        selected_sections: SectionNameCollection,
        keep_outdated: bool,
        logger: logging.Logger,
    ) -> None:
        self.config_cache: Final = config_cache
        self.selected_sections: Final = selected_sections
        self.keep_outdated: Final = keep_outdated
        self.logger: Final = logger

    def __call__(
        self,
        fetched: Iterable[tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception]]],
    ) -> Sequence[tuple[SourceInfo, result.Result[HostSections, Exception]]]:
        """Parse fetched data."""
        console.vverbose("%s+%s %s\n", tty.yellow, tty.normal, "Parse fetcher results".upper())
        output: list[tuple[SourceInfo, result.Result[HostSections, Exception]]] = []
        # Special agents can produce data for the same check_plugin_name on the same host, in this case
        # the section lines need to be extended
        for source, raw_data in fetched:
            source_result = parse_raw_data(
                make_parser(
                    self.config_cache,
                    source,
                    checking_sections=self.config_cache.make_checking_sections(
                        source.hostname, selected_sections=NO_SELECTION
                    ),
                    keep_outdated=self.keep_outdated,
                    logger=self.logger,
                ),
                raw_data,
                selection=self.selected_sections,
            )
            output.append((source, source_result))
        return output


class ConfiguredSummarizer:
    def __init__(
        self,
        config_cache: ConfigCache,
        host_name: HostName,
        *,
        include_ok_results: bool,
        override_non_ok_state: ServiceState | None = None,
    ) -> None:
        self.config_cache: Final = config_cache
        self.host_name: Final = host_name
        self.include_ok_results: Final = include_ok_results
        self.override_non_ok_state: Final = override_non_ok_state

    def __call__(
        self,
        host_sections: Iterable[tuple[SourceInfo, result.Result[HostSections, Exception]]],
    ) -> Iterable[ActiveCheckResult]:
        yield from (
            summarize_host_sections(
                host_sections,
                source,
                include_ok_results=self.include_ok_results,
                override_non_ok_state=self.override_non_ok_state,
                exit_spec=self.config_cache.exit_code_spec(source.hostname, source.ident),
                time_settings=self.config_cache.get_piggybacked_hosts_time_settings(
                    piggybacked_hostname=source.hostname
                ),
                is_piggyback=self.config_cache.is_piggyback_host(self.host_name),
            )
            for source, host_sections in host_sections
        )


def summarize_host_sections(
    host_sections: result.Result[HostSections, Exception],
    source: SourceInfo,
    *,
    include_ok_results: bool = False,
    override_non_ok_state: ServiceState | None = None,
    exit_spec: ExitSpec,
    time_settings: PiggybackTimeSettings,
    is_piggyback: bool,
) -> ActiveCheckResult:
    subresults = summarize(
        source.hostname,
        source.ipaddress,
        host_sections,
        exit_spec=exit_spec,
        time_settings=time_settings,
        is_piggyback=is_piggyback,
        fetcher_type=source.fetcher_type,
    )
    return (
        ActiveCheckResult()
        if not include_ok_results and all(s.state == 0 for s in subresults)
        else ActiveCheckResult.from_subresults(
            *(
                ActiveCheckResult(
                    s.state
                    if (s.state == 0 or override_non_ok_state is None)
                    else override_non_ok_state,
                    f"[{source.ident}] {s.summary}" if idx == 0 else s.summary,
                    s.details,
                    s.metrics,
                )
                for idx, s in enumerate(subresults)
            )
        )
    )


class ConfiguredFetcher:
    def __init__(
        self,
        config_cache: ConfigCache,
        *,
        # alphabetically sorted
        file_cache_options: FileCacheOptions,
        force_snmp_cache_refresh: bool,
        mode: Mode,
        on_error: OnError,
        selected_sections: SectionNameCollection,
        simulation_mode: bool,
        max_cachefile_age: MaxAge | None = None,
    ) -> None:
        self.config_cache: Final = config_cache
        self.file_cache_options: Final = file_cache_options
        self.force_snmp_cache_refresh: Final = force_snmp_cache_refresh
        self.mode: Final = mode
        self.on_error: Final = on_error
        self.selected_sections: Final = selected_sections
        self.simulation_mode: Final = simulation_mode
        self.max_cachefile_age: Final = max_cachefile_age

    def __call__(
        self, host_name: HostName, *, ip_address: HostAddress | None
    ) -> Sequence[
        tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception], Snapshot]
    ]:
        nodes = self.config_cache.nodes_of(host_name)
        if nodes is None:
            # In case of keepalive we always have an ipaddress (can be 0.0.0.0 or :: when
            # address is unknown). When called as non keepalive ipaddress may be None or
            # is already an address (2nd argument)
            hosts = [
                (host_name, ip_address or config.lookup_ip_address(self.config_cache, host_name))
            ]
        else:
            hosts = [(node, config.lookup_ip_address(self.config_cache, node)) for node in nodes]

        return _fetch_all(
            itertools.chain.from_iterable(
                make_sources(
                    host_name_,
                    ip_address_,
                    ConfigCache.address_family(host_name),
                    config_cache=self.config_cache,
                    force_snmp_cache_refresh=(
                        self.force_snmp_cache_refresh if nodes is None else False
                    ),
                    selected_sections=self.selected_sections if nodes is None else NO_SELECTION,
                    on_scan_error=self.on_error if nodes is None else OnError.RAISE,
                    simulation_mode=self.simulation_mode,
                    file_cache_options=self.file_cache_options,
                    file_cache_max_age=self.max_cachefile_age
                    or self.config_cache.max_cachefile_age(host_name),
                )
                for host_name_, ip_address_ in hosts
            ),
            simulation=self.simulation_mode,
            file_cache_options=self.file_cache_options,
            mode=self.mode,
        )


class SectionPluginMapper(Mapping[SectionName, PSectionPlugin]):
    # We should probably not tap into the private `register._config` module but
    # the data we need doesn't seem to be available elsewhere.  Anyway, this is
    # an *immutable* Mapping so we are actually on the safe side.

    def __getitem__(self, __key: SectionName) -> PSectionPlugin:
        return _api.get_section_plugin(__key)

    def __iter__(self) -> Iterator[SectionName]:
        return iter(
            frozenset(_api.registered_agent_sections) | frozenset(_api.registered_snmp_sections)
        )

    def __len__(self) -> int:
        return len(
            frozenset(_api.registered_agent_sections) | frozenset(_api.registered_snmp_sections)
        )


class HostLabelPluginMapper(Mapping[SectionName, PHostLabelDiscoveryPlugin]):
    def __getitem__(self, __key: SectionName) -> PHostLabelDiscoveryPlugin:
        return _api.get_section_plugin(__key)

    def __iter__(self) -> Iterator[SectionName]:
        return iter(
            frozenset(_api.registered_agent_sections) | frozenset(_api.registered_snmp_sections)
        )

    def __len__(self) -> int:
        return len(
            frozenset(_api.registered_agent_sections) | frozenset(_api.registered_snmp_sections)
        )


class CheckPluginMapper(Mapping[CheckPluginName, PCheckPlugin]):
    # See comment to SectionPluginMapper.
    def __getitem__(self, __key: CheckPluginName) -> PCheckPlugin:
        value = _api.get_check_plugin(__key)
        if value is None:
            raise KeyError(__key)
        return value

    def __iter__(self) -> Iterator[CheckPluginName]:
        return iter(_api.registered_check_plugins)

    def __len__(self) -> int:
        return len(_api.registered_check_plugins)


class DiscoveryPluginMapper(Mapping[CheckPluginName, PDiscoveryPlugin]):
    # See comment to SectionPluginMapper.
    def __getitem__(self, __key: CheckPluginName) -> PDiscoveryPlugin:
        # `get_check_plugin()` is not an error.  Both check plugins and
        # discovery are declared together in the check API.
        value = _api.get_check_plugin(__key)
        if value is None:
            raise KeyError(__key)
        return value

    def __iter__(self) -> Iterator[CheckPluginName]:
        return iter(_api.registered_check_plugins)

    def __len__(self) -> int:
        return len(_api.registered_check_plugins)


class InventoryPluginMapper(Mapping[InventoryPluginName, PInventoryPlugin]):
    # See comment to SectionPluginMapper.
    def __getitem__(self, __key: InventoryPluginName) -> PInventoryPlugin:
        return _api.registered_inventory_plugins[__key]

    def __iter__(self) -> Iterator[InventoryPluginName]:
        return iter(_api.registered_inventory_plugins)

    def __len__(self) -> int:
        return len(_api.registered_inventory_plugins)
