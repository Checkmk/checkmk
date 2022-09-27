#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO: Cluster with different data sources, eg. TCP node and SNMP node:
# - Discovery works.
# - Checking doesn't work - as it was before. Maybe we can handle this in the future.

from typing import Callable, Dict, Final, Iterable, List, Optional, Sequence, Tuple

import cmk.utils.tty as tty
from cmk.utils import version
from cmk.utils.cpu_tracking import CPUTracker
from cmk.utils.exceptions import OnError
from cmk.utils.log import console
from cmk.utils.translations import TranslationOptions
from cmk.utils.type_defs import HostAddress, HostName

import cmk.core_helpers.cache as file_cache
from cmk.core_helpers.protocol import FetcherMessage
from cmk.core_helpers.type_defs import NO_SELECTION, SectionNameCollection

import cmk.base.config as config
import cmk.base.core_config as core_config
from cmk.base.config import HostConfig

from ._abstract import Mode, Source
from .ipmi import IPMISource
from .piggyback import PiggybackSource
from .programs import DSProgramSource, SpecialAgentSource
from .snmp import SNMPSource
from .tcp import TCPSource

if version.is_plus_edition():
    # pylint: disable=no-name-in-module,import-error
    from cmk.base.cpe.sources.push_agent import PushAgentSource  # type: ignore[import]
else:

    class PushAgentSource:  # type: ignore[no-redef]
        def __init__(self, host_name, *a, **kw) -> None:  # type:ignore[no-untyped-def]
            raise NotImplementedError(
                f"[{host_name}]: connection mode 'push-agent' not available on "
                f"{version.edition().title}"
            )


__all__ = ["fetch_all", "make_non_cluster_sources", "make_cluster_sources", "make_sources"]


class _Builder:
    """Build a source list from host config and raw sections."""

    def __init__(
        self,
        host_config: HostConfig,
        ipaddress: Optional[HostAddress],
        *,
        selected_sections: SectionNameCollection,
        on_scan_error: OnError,
        force_snmp_cache_refresh: bool,
        simulation_mode: bool,
        agent_simulator: bool,
        translation: TranslationOptions,
        encoding_fallback: str,
        missing_sys_description: bool,
    ) -> None:
        super().__init__()
        self.host_config: Final = host_config
        self.ipaddress: Final = ipaddress
        self.selected_sections: Final = selected_sections
        self.on_scan_error: Final = on_scan_error
        self.force_snmp_cache_refresh: Final = force_snmp_cache_refresh
        self.simulation_mode: Final = simulation_mode
        self.agent_simulator: Final = agent_simulator
        self.translation: Final = translation
        self.encoding_fallback: Final = encoding_fallback
        self.missing_sys_description: Final = missing_sys_description
        self._elems: Dict[str, Source] = {}

        self._initialize()

    @property
    def sources(self) -> Sequence[Source]:
        # Always execute piggyback at the end
        return sorted(
            self._elems.values(),
            key=lambda c: (isinstance(c, PiggybackSource), c.id),
        )

    def _initialize(self) -> None:
        if self.host_config.is_cluster:
            # Cluster hosts do not have any actual data sources
            # Instead all data is provided by the nodes
            return

        self._initialize_agent_based()
        self._initialize_snmp_based()
        self._initialize_mgmt_boards()

    def _initialize_agent_based(self) -> None:
        if self.host_config.is_all_agents_host:
            self._add(
                self._get_agent(
                    ignore_special_agents=True,
                    main_data_source=True,
                )
            )
            for elem in self._get_special_agents():
                self._add(elem)

        elif self.host_config.is_all_special_agents_host:
            for elem in self._get_special_agents():
                self._add(elem)

        elif self.host_config.is_tcp_host:
            self._add(
                self._get_agent(
                    ignore_special_agents=False,
                    main_data_source=True,
                )
            )

        if "no-piggyback" not in self.host_config.tags:
            self._add(
                PiggybackSource(
                    self.host_config,
                    self.ipaddress,
                    simulation_mode=self.simulation_mode,
                    agent_simulator=self.agent_simulator,
                    time_settings=config.get_config_cache().get_piggybacked_hosts_time_settings(
                        piggybacked_hostname=self.host_config.hostname
                    ),
                    translation=self.translation,
                    encoding_fallback=self.encoding_fallback,
                )
            )

    def _initialize_snmp_based(self) -> None:
        if not self.host_config.is_snmp_host:
            return
        self._add(
            SNMPSource.snmp(
                self.host_config,
                self.ipaddress,
                selected_sections=self.selected_sections,
                on_scan_error=self.on_scan_error,
                force_cache_refresh=self.force_snmp_cache_refresh,
                simulation_mode=self.simulation_mode,
                missing_sys_description=self.missing_sys_description,
            )
        )

    def _initialize_mgmt_boards(self) -> None:
        protocol = self.host_config.management_protocol
        if protocol is None:
            return

        ip_address = config.lookup_mgmt_board_ip_address(self.host_config)
        if ip_address is None:
            # HostAddress is not Optional.
            #
            # See above.
            return
        if protocol == "snmp":
            self._add(
                SNMPSource.management_board(
                    self.host_config,
                    ip_address,
                    selected_sections=self.selected_sections,
                    on_scan_error=self.on_scan_error,
                    force_cache_refresh=self.force_snmp_cache_refresh,
                    simulation_mode=self.simulation_mode,
                    missing_sys_description=self.missing_sys_description,
                )
            )
        elif protocol == "ipmi":
            self._add(
                IPMISource(
                    self.host_config,
                    ip_address,
                    simulation_mode=self.simulation_mode,
                    agent_simulator=self.agent_simulator,
                    translation=self.translation,
                    encoding_fallback=self.encoding_fallback,
                )
            )
        else:
            raise LookupError()

    def _add(self, source: Source) -> None:
        self._elems[source.id] = source

    def _get_agent(
        self,
        ignore_special_agents: bool,
        main_data_source: bool,
    ) -> Source:
        if not ignore_special_agents:
            special_agents = self._get_special_agents()
            if special_agents:
                return special_agents[0]

        datasource_program = self.host_config.datasource_program
        if datasource_program is not None:
            return DSProgramSource(
                self.host_config,
                self.ipaddress,
                main_data_source=main_data_source,
                cmdline=core_config.translate_ds_program_source_cmdline(
                    datasource_program, self.host_config, self.ipaddress
                ),
                simulation_mode=self.simulation_mode,
                agent_simulator=self.agent_simulator,
                translation=self.translation,
                encoding_fallback=self.encoding_fallback,
            )

        connection_mode = self.host_config.agent_connection_mode()
        if connection_mode == "push-agent":
            return PushAgentSource(
                self.host_config,
                self.ipaddress,
                simulation_mode=self.simulation_mode,
                agent_simulator=self.agent_simulator,
                translation=self.translation,
                encoding_fallback=self.encoding_fallback,
            )
        if connection_mode == "pull-agent":
            return TCPSource(
                self.host_config,
                self.ipaddress,
                main_data_source=main_data_source,
                simulation_mode=self.simulation_mode,
                agent_simulator=self.agent_simulator,
                translation=self.translation,
                encoding_fallback=self.encoding_fallback,
            )
        raise NotImplementedError(f"connection mode {connection_mode!r}")

    def _get_special_agents(self) -> Sequence[Source]:
        return [
            SpecialAgentSource(
                self.host_config,
                self.ipaddress,
                agentname=agentname,
                cmdline=core_config.make_special_agent_cmdline(
                    self.host_config.hostname,
                    self.ipaddress,
                    agentname,
                    params,
                ),
                stdin=core_config.make_special_agent_stdin(
                    self.host_config.hostname,
                    self.ipaddress,
                    agentname,
                    params,
                ),
                simulation_mode=self.simulation_mode,
                agent_simulator=self.agent_simulator,
                translation=self.translation,
                encoding_fallback=self.encoding_fallback,
            )
            for agentname, params in self.host_config.special_agents
        ]


def make_non_cluster_sources(
    host_config: HostConfig,
    ipaddress: Optional[HostAddress],
    *,
    force_snmp_cache_refresh: bool = False,
    selected_sections: SectionNameCollection = NO_SELECTION,
    on_scan_error: OnError = OnError.RAISE,
    simulation_mode: bool,
    agent_simulator: bool,
    translation: TranslationOptions,
    encoding_fallback: str,
    missing_sys_description: bool,
) -> Sequence[Source]:
    """Sequence of sources available for `host_config`."""
    return _Builder(
        host_config,
        ipaddress,
        selected_sections=selected_sections,
        on_scan_error=on_scan_error,
        force_snmp_cache_refresh=force_snmp_cache_refresh,
        simulation_mode=simulation_mode,
        agent_simulator=agent_simulator,
        translation=translation,
        encoding_fallback=encoding_fallback,
        missing_sys_description=missing_sys_description,
    ).sources


def fetch_all(
    sources: Iterable[Source],
    *,
    file_cache_max_age: file_cache.MaxAge,
    mode: Mode,
) -> Sequence[Tuple[Source, FetcherMessage]]:
    console.verbose("%s+%s %s\n", tty.yellow, tty.normal, "Fetching data".upper())
    out: List[Tuple[Source, FetcherMessage]] = []
    for source in sources:
        console.vverbose("  Source: %s/%s\n" % (source.source_type, source.fetcher_type))

        source.file_cache_max_age = file_cache_max_age

        with CPUTracker() as tracker:
            raw_data = source.fetch(mode)
        out.append(
            (
                source,
                FetcherMessage.from_raw_data(
                    raw_data,
                    tracker.duration,
                    source.fetcher_type,
                ),
            )
        )
    return out


def make_cluster_sources(
    host_config: HostConfig,
    *,
    ip_lookup: Callable[[HostName], Optional[HostAddress]],
    simulation_mode: bool,
    agent_simulator: bool,
    translation: TranslationOptions,
    encoding_fallback: str,
    missing_sys_description: bool,
) -> Sequence[Source]:
    """Abstract clusters/nodes/hosts"""
    assert host_config.nodes is not None

    return [
        source
        for host_name in host_config.nodes
        for source in make_non_cluster_sources(
            HostConfig.make_host_config(host_name),
            ip_lookup(host_name),
            force_snmp_cache_refresh=False,
            simulation_mode=simulation_mode,
            agent_simulator=agent_simulator,
            translation=translation,
            encoding_fallback=encoding_fallback,
            missing_sys_description=missing_sys_description,
        )
    ]


def make_sources(
    host_config: HostConfig,
    ip_address: Optional[HostAddress],
    *,
    ip_lookup: Callable[[HostName], Optional[HostAddress]],
    selected_sections: SectionNameCollection,
    force_snmp_cache_refresh: bool,
    on_scan_error: OnError,
    simulation_mode: bool,
    agent_simulator: bool,
    translation: TranslationOptions,
    encoding_fallback: str,
    missing_sys_description: bool,
) -> Sequence[Source]:
    return (
        make_non_cluster_sources(
            host_config,
            ip_address,
            selected_sections=selected_sections,
            force_snmp_cache_refresh=force_snmp_cache_refresh,
            on_scan_error=on_scan_error,
            simulation_mode=simulation_mode,
            agent_simulator=agent_simulator,
            translation=translation,
            encoding_fallback=encoding_fallback,
            missing_sys_description=missing_sys_description,
        )
        if host_config.nodes is None
        else make_cluster_sources(
            host_config,
            ip_lookup=ip_lookup,
            simulation_mode=simulation_mode,
            agent_simulator=agent_simulator,
            translation=translation,
            encoding_fallback=encoding_fallback,
            missing_sys_description=missing_sys_description,
        )
    )
