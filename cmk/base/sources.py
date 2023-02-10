#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO: Cluster with different data sources, eg. TCP node and SNMP node:
# - Discovery works.
# - Checking doesn't work - as it was before. Maybe we can handle this in the future.

import logging
from collections.abc import Iterable, Sequence
from contextlib import suppress
from typing import Final

from cmk.utils.exceptions import OnError
from cmk.utils.type_defs import HostAddress, HostName, SectionName

from cmk.snmplib.type_defs import SNMPRawDataSection

from cmk.fetchers import (
    Fetcher,
    FetcherType,
    NoFetcher,
    ProgramFetcher,
    SNMPFetcher,
    SourceInfo,
    SourceType,
)
from cmk.fetchers.cache import SectionStore
from cmk.fetchers.config import make_file_cache_path_template, make_persisted_section_dir
from cmk.fetchers.filecache import (
    AgentFileCache,
    FileCache,
    FileCacheMode,
    FileCacheOptions,
    MaxAge,
    SNMPFileCache,
)

from cmk.checkers import Parser, SNMPParser
from cmk.checkers.type_defs import AgentRawDataSection, NO_SELECTION, SectionNameCollection

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.config as config
import cmk.base.core_config as core_config
from cmk.base.api.agent_based.register.snmp_plugin_store import make_plugin_store
from cmk.base.config import ConfigCache

__all__ = [
    "make_sources",
    "make_parser",
]


def ensure_ipaddress(address: HostAddress | None) -> HostAddress:
    if address is None:
        raise TypeError(address)
    if address in ["0.0.0.0", "::"]:
        raise TypeError(address)
    return address


def make_parser(
    config_cache: ConfigCache,
    source: SourceInfo,
    *,
    # Always from NO_SELECTION.
    checking_sections: frozenset[SectionName],
    keep_outdated: bool,
    logger: logging.Logger,
) -> Parser:
    hostname = source.hostname
    if source.fetcher_type is FetcherType.SNMP:
        return SNMPParser(
            hostname,
            SectionStore[SNMPRawDataSection](
                make_persisted_section_dir(
                    source.hostname,
                    fetcher_type=source.fetcher_type,
                    ident=source.ident,
                ),
                logger=logger,
            ),
            check_intervals={
                section_name: config_cache.snmp_fetch_interval(hostname, section_name)
                for section_name in checking_sections
            },
            keep_outdated=keep_outdated,
            logger=logger,
        )

    return config_cache.make_agent_parser(
        hostname,
        SectionStore[AgentRawDataSection](
            make_persisted_section_dir(
                source.hostname, fetcher_type=source.fetcher_type, ident=source.ident
            ),
            logger=logger,
        ),
        keep_outdated=keep_outdated,
        logger=logger,
    )


class _Builder:
    """Build a source list from host config and raw sections."""

    def __init__(
        self,
        host_name: HostName,
        ipaddress: HostAddress | None,
        *,
        config_cache: ConfigCache,
        selected_sections: SectionNameCollection,
        on_scan_error: OnError,
        force_snmp_cache_refresh: bool,
        simulation_mode: bool,
        file_cache_options: FileCacheOptions,
        file_cache_max_age: MaxAge,
    ) -> None:
        super().__init__()
        self.host_name: Final = host_name
        self.config_cache: Final = config_cache
        self.ipaddress: Final = ipaddress
        self.selected_sections: Final = selected_sections
        self.on_scan_error: Final = on_scan_error
        self.force_snmp_cache_refresh: Final = force_snmp_cache_refresh
        self.simulation_mode: Final = simulation_mode
        self.file_cache_options: Final = file_cache_options
        self.file_cache_max_age: Final = file_cache_max_age
        self._elems: dict[str, tuple[SourceInfo, FileCache, Fetcher]] = {}

        self._initialize()

    @property
    def sources(self) -> Sequence[tuple[SourceInfo, FileCache, Fetcher]]:
        # Always execute piggyback at the end
        return sorted(
            self._elems.values(),
            key=lambda args: (
                args[0].fetcher_type is FetcherType.PIGGYBACK,
                args[0].ident,
            ),
        )

    def _initialize(self) -> None:
        if self.config_cache.is_cluster(self.host_name):
            # Cluster hosts do not have any actual data sources
            # Instead all data is provided by the nodes
            return

        self._initialize_agent_based()
        self._initialize_snmp_based()
        self._initialize_mgmt_boards()

    def _initialize_agent_based(self) -> None:
        # agent-based data sources use the cache and persisted directories
        # that existed before the data source concept has been added where
        # each data source has its own set of directories.
        #
        # TODO: We should cleanup these old directories one day, then we can
        #       remove this special case.
        #
        if self.config_cache.is_all_agents_host(self.host_name):
            with suppress(TypeError):
                self._add(*self._get_agent())
            for elem in self._get_special_agents():
                self._add(*elem)

        elif self.config_cache.is_all_special_agents_host(self.host_name):
            for elem in self._get_special_agents():
                self._add(*elem)

        elif self.config_cache.is_tcp_host(self.host_name):
            special_agents = tuple(self._get_special_agents())
            if special_agents:
                self._add(*special_agents[0])
            else:
                with suppress(TypeError):
                    self._add(*self._get_agent())

        if "no-piggyback" not in self.config_cache.tag_list(self.host_name):
            source = SourceInfo(
                self.host_name,
                self.ipaddress,
                "piggyback",
                FetcherType.PIGGYBACK,
                SourceType.HOST,
            )
            self._add(
                source,
                self.config_cache.make_piggyback_fetcher(source.hostname, source.ipaddress),
                AgentFileCache(
                    source.hostname,
                    path_template=make_file_cache_path_template(
                        fetcher_type=source.fetcher_type, ident=source.ident
                    ),
                    max_age=MaxAge.unlimited()
                    if self.file_cache_options.use_outdated
                    else self.file_cache_max_age,
                    simulation=False,  # TODO Quickfix for SUP-9912
                    use_only_cache=self.file_cache_options.use_only_cache,
                    file_cache_mode=FileCacheMode.DISABLED,
                ),
            )

    def _initialize_snmp_plugin_store(self) -> None:
        if len(SNMPFetcher.plugin_store) != agent_based_register.len_snmp_sections():
            # That's a hack.
            #
            # `make_plugin_store()` depends on
            # `iter_all_snmp_sections()` and `iter_all_inventory_plugins()`
            # that are populated by the Check API upon loading the plugins.
            #
            # It is there, when the plugins are loaded, that we should
            # make the plugin store.  However, it is not clear whether
            # the API would let us register hooks to accomplish that.
            #
            # The current solution is brittle in that there is not guarantee
            # that all the relevant plugins are loaded at this point.
            SNMPFetcher.plugin_store = make_plugin_store()

    def _initialize_snmp_based(self) -> None:
        if not self.config_cache.is_snmp_host(self.host_name):
            return
        self._initialize_snmp_plugin_store()
        source = SourceInfo(
            self.host_name,
            self.ipaddress,
            "snmp",
            FetcherType.SNMP,
            SourceType.HOST,
        )
        with suppress(TypeError):
            self._add(
                source,
                self.config_cache.make_snmp_fetcher(
                    self.host_name,
                    ensure_ipaddress(self.ipaddress),
                    on_scan_error=self.on_scan_error,
                    selected_sections=self.selected_sections,
                ),
                SNMPFileCache(
                    source.hostname,
                    path_template=make_file_cache_path_template(
                        fetcher_type=source.fetcher_type, ident=source.ident
                    ),
                    max_age=self._max_age_snmp(),
                    simulation=self.simulation_mode,
                    use_only_cache=self.file_cache_options.use_only_cache,
                    file_cache_mode=self.file_cache_options.file_cache_mode(),
                ),
            )

    def _initialize_mgmt_boards(self) -> None:
        protocol = self.config_cache.management_protocol(self.host_name)
        if protocol is None:
            return

        self._initialize_snmp_plugin_store()
        if protocol == "snmp":
            with suppress(TypeError):
                source = SourceInfo(
                    self.host_name,
                    ensure_ipaddress(self.ipaddress),
                    "mgmt_snmp",
                    FetcherType.SNMP,
                    SourceType.MANAGEMENT,
                )
                self._add(
                    source,
                    self.config_cache.make_snmp_fetcher(
                        source.hostname,
                        ensure_ipaddress(source.ipaddress),
                        on_scan_error=self.on_scan_error,
                        selected_sections=self.selected_sections,
                    ),
                    SNMPFileCache(
                        source.hostname,
                        path_template=make_file_cache_path_template(
                            fetcher_type=source.fetcher_type, ident=source.ident
                        ),
                        max_age=self._max_age_snmp(),
                        simulation=self.simulation_mode,
                        use_only_cache=self.file_cache_options.use_only_cache,
                        file_cache_mode=self.file_cache_options.file_cache_mode(),
                    ),
                )
        elif protocol == "ipmi":
            with suppress(TypeError):
                source = SourceInfo(
                    self.host_name,
                    ensure_ipaddress(
                        config.lookup_mgmt_board_ip_address(self.config_cache, self.host_name)
                    ),
                    "mgmt_ipmi",
                    FetcherType.IPMI,
                    SourceType.MANAGEMENT,
                )
                self._add(
                    source,
                    self.config_cache.make_ipmi_fetcher(
                        source.hostname, ensure_ipaddress(source.ipaddress)
                    ),
                    AgentFileCache(
                        source.hostname,
                        path_template=make_file_cache_path_template(
                            fetcher_type=source.fetcher_type, ident=source.ident
                        ),
                        max_age=self._max_age_tcp(),
                        simulation=self.simulation_mode,
                        use_only_cache=self.file_cache_options.use_only_cache,
                        file_cache_mode=self.file_cache_options.file_cache_mode(),
                    ),
                )
        else:
            raise LookupError()

    def _add(self, source: SourceInfo, fetcher: Fetcher, file_cache: FileCache) -> None:
        self._elems[source.ident] = (
            source,
            file_cache,
            fetcher,
        )

    def _get_agent(self) -> tuple[SourceInfo, Fetcher, FileCache]:
        with suppress(LookupError):
            source = SourceInfo(
                self.host_name,
                self.ipaddress,
                "agent",
                FetcherType.PROGRAM,
                SourceType.HOST,
            )
            return (
                source,
                self.config_cache.make_program_fetcher(source.hostname, source.ipaddress),
                AgentFileCache(
                    source.hostname,
                    path_template=make_file_cache_path_template(
                        fetcher_type=source.fetcher_type, ident=source.ident
                    ),
                    max_age=self._max_age_tcp(),
                    simulation=self.simulation_mode,
                    use_only_cache=self.file_cache_options.use_only_cache,
                    file_cache_mode=self.file_cache_options.file_cache_mode(),
                ),
            )

        connection_mode = self.config_cache.agent_connection_mode(self.host_name)
        if connection_mode == "push-agent":
            source = SourceInfo(
                self.host_name,
                self.ipaddress,
                "push-agent",
                FetcherType.PUSH_AGENT,
                SourceType.HOST,
            )
            # convert to seconds and add grace period
            interval = int(1.5 * 60 * self.config_cache.check_mk_check_interval(self.host_name))
            return (
                source,
                NoFetcher(),
                AgentFileCache(
                    source.hostname,
                    path_template=make_file_cache_path_template(
                        fetcher_type=source.fetcher_type, ident=source.ident
                    ),
                    max_age=MaxAge.unlimited()
                    if self.simulation_mode or self.file_cache_options.use_outdated
                    else MaxAge(interval, interval, interval),
                    simulation=self.simulation_mode,
                    use_only_cache=True,
                    file_cache_mode=(
                        # Careful: at most read-only!
                        FileCacheMode.DISABLED
                        if self.file_cache_options.disabled
                        else FileCacheMode.READ
                    ),
                ),
            )
        if connection_mode == "pull-agent":
            source = SourceInfo(
                self.host_name,
                self.ipaddress,
                "agent",
                FetcherType.TCP,
                SourceType.HOST,
            )
            return (
                source,
                self.config_cache.make_tcp_fetcher(
                    source.hostname, ensure_ipaddress(source.ipaddress)
                ),
                AgentFileCache(
                    source.hostname,
                    path_template=make_file_cache_path_template(
                        fetcher_type=source.fetcher_type, ident=source.ident
                    ),
                    max_age=self._max_age_tcp(),
                    simulation=self.simulation_mode,
                    use_only_cache=self.file_cache_options.tcp_use_only_cache
                    or self.file_cache_options.use_only_cache,
                    file_cache_mode=self.file_cache_options.file_cache_mode(),
                ),
            )
        raise NotImplementedError(f"connection mode {connection_mode!r}")

    def _get_special_agents(self) -> Iterable[tuple[SourceInfo, Fetcher, FileCache]]:
        def make_id(agentname: str) -> str:
            return f"special_{agentname}"

        for agentname, params in self.config_cache.special_agents(self.host_name):
            source = SourceInfo(
                self.host_name,
                self.ipaddress,
                make_id(agentname),
                FetcherType.SPECIAL_AGENT,
                SourceType.HOST,
            )
            fetcher = ProgramFetcher(
                cmdline=core_config.make_special_agent_cmdline(
                    self.host_name,
                    self.ipaddress,
                    agentname,
                    params,
                ),
                stdin=core_config.make_special_agent_stdin(
                    self.host_name,
                    self.ipaddress,
                    agentname,
                    params,
                ),
                is_cmc=config.is_cmc(),
            )
            file_cache = AgentFileCache(
                source.hostname,
                path_template=make_file_cache_path_template(
                    fetcher_type=source.fetcher_type, ident=source.ident
                ),
                max_age=self._max_age_tcp(),
                simulation=self.simulation_mode,
                use_only_cache=self.file_cache_options.use_only_cache,
                file_cache_mode=self.file_cache_options.file_cache_mode(),
            )
            yield source, fetcher, file_cache

    def _max_age_snmp(self) -> MaxAge:
        if self.simulation_mode:
            return MaxAge.unlimited()
        if self.force_snmp_cache_refresh:
            return MaxAge.zero()
        if self.file_cache_options.use_outdated:
            return MaxAge.unlimited()
        return self.file_cache_max_age

    def _max_age_tcp(self) -> MaxAge:
        if self.simulation_mode:
            return MaxAge.unlimited()
        if self.file_cache_options.use_outdated:
            return MaxAge.unlimited()
        return self.file_cache_max_age


def make_sources(
    host_name: HostName,
    ipaddress: HostAddress | None,
    *,
    config_cache: ConfigCache,
    force_snmp_cache_refresh: bool = False,
    selected_sections: SectionNameCollection = NO_SELECTION,
    on_scan_error: OnError = OnError.RAISE,
    simulation_mode: bool,
    file_cache_options: FileCacheOptions,
    file_cache_max_age: MaxAge,
) -> Sequence[tuple[SourceInfo, FileCache, Fetcher]]:
    """Sequence of sources available for `host_config`."""
    return _Builder(
        host_name,
        ipaddress,
        config_cache=config_cache,
        selected_sections=selected_sections,
        on_scan_error=on_scan_error,
        force_snmp_cache_refresh=force_snmp_cache_refresh,
        simulation_mode=simulation_mode,
        file_cache_options=file_cache_options,
        file_cache_max_age=file_cache_max_age,
    ).sources
