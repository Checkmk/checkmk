#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO: Cluster with different data sources, eg. TCP node and SNMP node:
# - Discovery works.
# - Checking doesn't work - as it was before. Maybe we can handle this in the future.

import logging
from collections.abc import Iterable, Sequence
from contextlib import suppress
from pathlib import Path
from typing import assert_never, Final

import cmk.utils.password_store
from cmk.utils.agent_registration import HostAgentConnectionMode
from cmk.utils.exceptions import OnError
from cmk.utils.hostaddress import HostAddress, HostName
from cmk.utils.sectionname import SectionName

from cmk.snmplib import SNMPBackendEnum, SNMPRawDataElem

from cmk.fetchers import SNMPFetcher
from cmk.fetchers.config import make_persisted_section_dir
from cmk.fetchers.filecache import FileCacheOptions, MaxAge

from cmk.checkengine.fetcher import FetcherType, SourceInfo
from cmk.checkengine.parser import (
    AgentRawDataSectionElem,
    NO_SELECTION,
    Parser,
    SectionNameCollection,
    SectionStore,
    SNMPParser,
)

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.config as config
import cmk.base.server_side_calls as server_side_calls
from cmk.base.api.agent_based.register.snmp_plugin_store import make_plugin_store
from cmk.base.config import ConfigCache
from cmk.base.ip_lookup import AddressFamily
from cmk.base.server_side_calls import load_special_agents

from ._api import Source
from ._sources import (
    IPMISource,
    MgmtSNMPSource,
    MissingIPSource,
    MissingSourceSource,
    PiggybackSource,
    ProgramSource,
    PushAgentSource,
    SNMPSource,
    SpecialAgentSource,
    TCPSource,
)

__all__ = ["make_sources", "make_parser"]


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
            SectionStore[SNMPRawDataElem](
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
        SectionStore[Sequence[AgentRawDataSectionElem]](
            make_persisted_section_dir(
                source.hostname, fetcher_type=source.fetcher_type, ident=source.ident
            ),
            logger=logger,
        ),
        keep_outdated=keep_outdated,
        logger=logger,
    )


class _Builder:
    def __init__(
        self,
        host_name: HostName,
        ipaddress: HostAddress | None,
        address_family: AddressFamily,
        *,
        simulation_mode: bool,
        config_cache: ConfigCache,
        is_cluster: bool,
        selected_sections: SectionNameCollection,
        on_scan_error: OnError,
        max_age_agent: MaxAge,
        max_age_snmp: MaxAge,
        snmp_backend_override: SNMPBackendEnum | None,
        oid_cache_dir: Path,
    ) -> None:
        super().__init__()
        assert not is_cluster

        self.host_name: Final = host_name
        self.config_cache: Final = config_cache
        self.ipaddress: Final = ipaddress
        self.address_family: Final = address_family
        self.simulation_mode: Final = simulation_mode
        self.selected_sections: Final = selected_sections
        self.on_scan_error: Final = on_scan_error
        self.max_age_agent: Final = max_age_agent
        self.max_age_snmp: Final = max_age_snmp
        self.snmp_backend_override: Final = snmp_backend_override
        self._cds: Final = config_cache.computed_datasources(host_name)
        self._oid_cache_dir: Final = oid_cache_dir

        self._elems: dict[str, Source] = {}
        self._initialize_agent_based()

        if self._cds.is_tcp and not self._elems:
            # User wants a special agent, a CheckMK agent, or both.  But
            # we didn't configure anything.  Let's report that.
            self._add(MissingSourceSource(self.host_name, self.ipaddress, "API/agent"))

        if "no-piggyback" not in self.config_cache.tag_list(self.host_name):
            self._add(PiggybackSource(self.config_cache, self.host_name, self.ipaddress))

        self._initialize_snmp_based()
        self._initialize_mgmt_boards()

    @property
    def sources(self) -> Sequence[Source]:
        # Always execute piggyback at the end
        return sorted(
            self._elems.values(),
            key=lambda args: (
                args.source_info().fetcher_type is FetcherType.PIGGYBACK,
                args.source_info().ident,
            ),
        )

    def _initialize_agent_based(self) -> None:
        def make_special_agents() -> Iterable[Source]:
            for agentname, params in self.config_cache.special_agents(self.host_name):
                host_attrs = self.config_cache.get_host_attributes(self.host_name)
                macros = {
                    "<IP>": self.ipaddress or "",
                    "<HOST>": self.host_name,
                    **self.config_cache.get_host_macros_from_attributes(self.host_name, host_attrs),
                }
                special_agent = server_side_calls.SpecialAgent(
                    load_special_agents()[1],
                    config.special_agent_info,
                    self.host_name,
                    self.ipaddress,
                    config.get_ssc_host_config(self.host_name, self.config_cache, macros),
                    host_attrs,
                    config.http_proxies,
                    cmk.utils.password_store.load(),
                )
                for agent_data in special_agent.iter_special_agent_commands(agentname, params):
                    yield SpecialAgentSource(
                        self.config_cache,
                        self.host_name,
                        self.ipaddress,
                        max_age=self.max_age_agent,
                        agent_name=agentname,
                        cmdline=agent_data.cmdline,
                        stdin=agent_data.stdin,
                    )

        special_agents = tuple(make_special_agents())

        # Translation of the options from WATO (properties of host > monitoring agents)
        #
        #                           all_special_agents  all_agents_host  tcp_host
        # API else CheckMK agent     False               False            True
        # API and Checkmk agent      False               True             True
        # API, no Checkmk agent      True                False            True
        # no API, no Checkmk agent   False               False            False

        if self._cds.is_all_agents_host:
            self._add_agent()
            for elem in special_agents:
                self._add(elem)

        elif self._cds.is_all_special_agents_host:
            for elem in special_agents:
                self._add(elem)

        elif self._cds.is_tcp:
            if special_agents:
                self._add(special_agents[0])
            else:
                self._add_agent()

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
        if not self._cds.is_snmp:
            return

        self._initialize_snmp_plugin_store()

        if (
            self.simulation_mode
            or self.config_cache.get_snmp_backend(self.host_name) is SNMPBackendEnum.STORED_WALK
        ):
            # Here, we bypass NO_IP and silently set the IP to localhost.  This is to accomodate
            # our file-based simulation modes.  However, NO_IP should really be treated as a
            # configuration error with SNMP.  We should try to find a better solution in the future.
            self._add(
                SNMPSource(
                    self.config_cache,
                    self.host_name,
                    self.ipaddress or HostAddress("127.0.0.1"),
                    max_age=self.max_age_snmp,
                    on_scan_error=self.on_scan_error,
                    selected_sections=self.selected_sections,
                    backend_override=self.snmp_backend_override,
                    oid_cache_dir=self._oid_cache_dir,
                )
            )
            return

        if self.address_family is AddressFamily.NO_IP:
            return

        if self.ipaddress is None:
            self._add(MissingIPSource(self.host_name, self.ipaddress, "snmp"))
            return

        self._add(
            SNMPSource(
                self.config_cache,
                self.host_name,
                self.ipaddress,
                max_age=self.max_age_snmp,
                on_scan_error=self.on_scan_error,
                selected_sections=self.selected_sections,
                backend_override=self.snmp_backend_override,
                oid_cache_dir=self._oid_cache_dir,
            )
        )

    def _initialize_mgmt_boards(self) -> None:
        if self.address_family is AddressFamily.NO_IP:
            return

        protocol = self.config_cache.management_protocol(self.host_name)
        if protocol is None:
            return

        ip_address = config.lookup_mgmt_board_ip_address(self.config_cache, self.host_name)
        if ip_address is None:
            self._add(MissingIPSource(self.host_name, ip_address, f"mgmt_{protocol}"))
            return

        match protocol:
            case "snmp":
                self._initialize_snmp_plugin_store()
                self._add(
                    MgmtSNMPSource(
                        self.config_cache,
                        self.host_name,
                        ip_address,
                        max_age=self.max_age_snmp,
                        on_scan_error=self.on_scan_error,
                        selected_sections=self.selected_sections,
                        backend_override=self.snmp_backend_override,
                        oid_cache_dir=self._oid_cache_dir,
                    )
                )
            case "ipmi":
                self._add(
                    IPMISource(
                        self.config_cache, self.host_name, ip_address, max_age=self.max_age_agent
                    )
                )
            case _:
                assert_never(protocol)

    def _add(self, source: Source) -> None:
        self._elems[source.source_info().ident] = source

    def _add_agent(self) -> None:
        with suppress(LookupError):
            self._add(
                ProgramSource(
                    self.config_cache,
                    self.host_name,
                    self.ipaddress,
                    max_age=self.max_age_agent,
                )
            )
            return

        connection_mode = self.config_cache.agent_connection_mode(self.host_name)
        match connection_mode:
            case HostAgentConnectionMode.PUSH:
                # add grace period
                interval = int(1.5 * self.config_cache.check_mk_check_interval(self.host_name))
                self._add(
                    source=PushAgentSource(
                        self.host_name,
                        self.ipaddress,
                        max_age=MaxAge(interval, interval, interval),
                    )
                )
            case HostAgentConnectionMode.PULL:
                if self.address_family is AddressFamily.NO_IP:
                    return
                if self.ipaddress is None:
                    self._add(MissingIPSource(self.host_name, self.ipaddress, "agent"))
                    return
                self._add(
                    TCPSource(
                        self.config_cache,
                        self.host_name,
                        self.ipaddress,
                        max_age=self.max_age_agent,
                    )
                )
            case _:
                assert_never(connection_mode)


def make_sources(
    host_name: HostName,
    ipaddress: HostAddress | None,
    address_family: AddressFamily,
    *,
    config_cache: ConfigCache,
    is_cluster: bool,
    force_snmp_cache_refresh: bool = False,
    selected_sections: SectionNameCollection = NO_SELECTION,
    on_scan_error: OnError = OnError.RAISE,
    simulation_mode: bool,
    file_cache_options: FileCacheOptions,
    file_cache_max_age: MaxAge,
    snmp_backend_override: SNMPBackendEnum | None,
    oid_cache_dir: Path,
) -> Sequence[Source]:
    """Sequence of sources available for `host_config`."""
    if is_cluster:
        # Cluster hosts do not have any actual data sources
        # Instead all data is provided by the nodes
        return ()

    def max_age_snmp() -> MaxAge:
        if simulation_mode:
            return MaxAge.unlimited()
        if force_snmp_cache_refresh:
            return MaxAge.zero()
        if file_cache_options.use_outdated:
            return MaxAge.unlimited()
        return file_cache_max_age

    def max_age_agent() -> MaxAge:
        if simulation_mode:
            return MaxAge.unlimited()
        if file_cache_options.use_outdated:
            return MaxAge.unlimited()
        return file_cache_max_age

    return _Builder(
        host_name,
        ipaddress,
        address_family,
        simulation_mode=simulation_mode,
        config_cache=config_cache,
        is_cluster=is_cluster,
        selected_sections=selected_sections,
        on_scan_error=on_scan_error,
        max_age_agent=max_age_agent(),
        max_age_snmp=max_age_snmp(),
        snmp_backend_override=snmp_backend_override,
        oid_cache_dir=oid_cache_dir,
    ).sources
