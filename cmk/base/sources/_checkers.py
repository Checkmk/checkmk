#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO: Cluster with different data sources, eg. TCP node and SNMP node:
# - Discovery works.
# - Checking doesn't work - as it was before. Maybe we can handle this in the future.

from typing import (
    Callable,
    Dict,
    Final,
    FrozenSet,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
)

import cmk.utils.tty as tty
from cmk.utils import version
from cmk.utils.cpu_tracking import CPUTracker
from cmk.utils.exceptions import OnError
from cmk.utils.log import console
from cmk.utils.translations import TranslationOptions
from cmk.utils.type_defs import HostAddress, HostName, SectionName

from cmk.snmplib.type_defs import BackendSNMPTree, SNMPDetectSpec

import cmk.core_helpers.cache as file_cache
from cmk.core_helpers.protocol import FetcherMessage
from cmk.core_helpers.snmp import SectionMeta, SNMPFetcher, SNMPPluginStore, SNMPPluginStoreItem
from cmk.core_helpers.type_defs import NO_SELECTION, SectionNameCollection

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.check_table as check_table
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
        def __init__(self, host_name: HostName, *args: object, **kw: object) -> None:
            raise NotImplementedError(
                f"[{host_name}]: connection mode 'push-agent' not available on "
                f"{version.edition().title}"
            )


__all__ = ["fetch_all", "make_non_cluster_sources", "make_cluster_sources", "make_sources"]


def _make_inventory_sections() -> FrozenSet[SectionName]:
    return frozenset(
        s
        for s in agent_based_register.get_relevant_raw_sections(
            check_plugin_names=(),
            inventory_plugin_names=(
                p.name for p in agent_based_register.iter_all_inventory_plugins()
            ),
        )
        if agent_based_register.is_registered_snmp_section_plugin(s)
    )


def make_plugin_store() -> SNMPPluginStore:
    inventory_sections = _make_inventory_sections()
    return SNMPPluginStore(
        {
            s.name: SNMPPluginStoreItem(
                [BackendSNMPTree.from_frontend(base=t.base, oids=t.oids) for t in s.trees],
                SNMPDetectSpec(s.detect_spec),
                s.name in inventory_sections,
            )
            for s in agent_based_register.iter_all_snmp_sections()
        }
    )


def make_check_intervals(
    host_config: HostConfig,
    *,
    selected_sections: SectionNameCollection,
) -> Mapping[SectionName, Optional[int]]:
    return {
        section_name: host_config.snmp_fetch_interval(section_name)
        for section_name in _make_checking_sections(
            host_config.hostname, selected_sections=selected_sections
        )
    }


def make_sections(
    host_config: HostConfig,
    *,
    selected_sections: SectionNameCollection,
) -> Dict[SectionName, SectionMeta]:
    def needs_redetection(section_name: SectionName) -> bool:
        section = agent_based_register.get_section_plugin(section_name)
        return len(agent_based_register.get_section_producers(section.parsed_section_name)) > 1

    checking_sections = _make_checking_sections(
        host_config.hostname,
        selected_sections=selected_sections,
    )
    disabled_sections = host_config.disabled_snmp_sections()
    return {
        name: SectionMeta(
            checking=name in checking_sections,
            disabled=name in disabled_sections,
            redetect=name in checking_sections and needs_redetection(name),
            fetch_interval=host_config.snmp_fetch_interval(name),
        )
        for name in (checking_sections | disabled_sections)
    }


def _make_checking_sections(
    hostname: HostName,
    *,
    selected_sections: SectionNameCollection,
) -> FrozenSet[SectionName]:
    if selected_sections is not NO_SELECTION:
        checking_sections = selected_sections
    else:
        checking_sections = frozenset(
            agent_based_register.get_relevant_raw_sections(
                check_plugin_names=check_table.get_check_table(
                    hostname,
                    filter_mode=check_table.FilterMode.INCLUDE_CLUSTERED,
                    skip_ignored=True,
                ).needed_check_names(),
                inventory_plugin_names=(),
            )
        )
    return frozenset(
        s for s in checking_sections if agent_based_register.is_registered_snmp_section_plugin(s)
    )


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
        file_cache_max_age: file_cache.MaxAge,
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
        self.file_cache_max_age: Final = file_cache_max_age
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
                    self.host_config.hostname,
                    self.ipaddress,
                    id_="piggyback",
                    simulation_mode=self.simulation_mode,
                    agent_simulator=self.agent_simulator,
                    time_settings=config.get_config_cache().get_piggybacked_hosts_time_settings(
                        piggybacked_hostname=self.host_config.hostname
                    ),
                    translation=self.translation,
                    encoding_fallback=self.encoding_fallback,
                    check_interval=self.host_config.check_mk_check_interval,
                    is_piggyback_host=self.host_config.is_piggyback_host,
                    file_cache_max_age=self.file_cache_max_age,
                )
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
        if not self.host_config.is_snmp_host:
            return
        self._initialize_snmp_plugin_store()
        self._add(
            SNMPSource.snmp(
                self.host_config.hostname,
                self.ipaddress,
                id_="snmp",
                on_scan_error=self.on_scan_error,
                force_cache_refresh=self.force_snmp_cache_refresh,
                simulation_mode=self.simulation_mode,
                missing_sys_description=self.missing_sys_description,
                sections=make_sections(
                    self.host_config,
                    selected_sections=self.selected_sections,
                ),
                check_intervals=make_check_intervals(
                    self.host_config,
                    selected_sections=self.selected_sections,
                ),
                snmp_config=self.host_config.snmp_config(self.ipaddress),
                do_status_data_inventory=self.host_config.do_status_data_inventory,
                file_cache_max_age=self.file_cache_max_age,
            )
        )

    def _initialize_mgmt_boards(self) -> None:
        protocol = self.host_config.management_protocol
        if protocol is None:
            return

        self._initialize_snmp_plugin_store()
        ip_address = config.lookup_mgmt_board_ip_address(self.host_config)
        if ip_address is None:
            # HostAddress is not Optional.
            #
            # See above.
            return
        if protocol == "snmp":
            self._add(
                SNMPSource.management_board(
                    self.host_config.hostname,
                    ip_address,
                    id_="mgmt_snmp",
                    on_scan_error=self.on_scan_error,
                    force_cache_refresh=self.force_snmp_cache_refresh,
                    simulation_mode=self.simulation_mode,
                    missing_sys_description=self.missing_sys_description,
                    sections=make_sections(
                        self.host_config, selected_sections=self.selected_sections
                    ),
                    check_intervals=make_check_intervals(
                        self.host_config, selected_sections=self.selected_sections
                    ),
                    snmp_config=self.host_config.management_snmp_config,
                    do_status_data_inventory=self.host_config.do_status_data_inventory,
                    file_cache_max_age=self.file_cache_max_age,
                )
            )
        elif protocol == "ipmi":
            self._add(
                IPMISource(
                    self.host_config.hostname,
                    ip_address,
                    id_="mgmt_ipmi",
                    simulation_mode=self.simulation_mode,
                    agent_simulator=self.agent_simulator,
                    translation=self.translation,
                    encoding_fallback=self.encoding_fallback,
                    check_interval=self.host_config.check_mk_check_interval,
                    management_credentials=self.host_config.ipmi_credentials,
                    file_cache_max_age=self.file_cache_max_age,
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
                self.host_config.hostname,
                self.ipaddress,
                id_="agent",
                main_data_source=main_data_source,
                cmdline=core_config.translate_ds_program_source_cmdline(
                    datasource_program, self.host_config, self.ipaddress
                ),
                simulation_mode=self.simulation_mode,
                agent_simulator=self.agent_simulator,
                translation=self.translation,
                encoding_fallback=self.encoding_fallback,
                check_interval=self.host_config.check_mk_check_interval,
                is_cmc=config.is_cmc(),
                file_cache_max_age=self.file_cache_max_age,
            )

        connection_mode = self.host_config.agent_connection_mode()
        if connection_mode == "push-agent":
            return PushAgentSource(
                self.host_config.hostname,
                self.ipaddress,
                id_="push-agent",
                simulation_mode=self.simulation_mode,
                agent_simulator=self.agent_simulator,
                translation=self.translation,
                encoding_fallback=self.encoding_fallback,
                check_interval=self.host_config.check_mk_check_interval,
                file_cache_max_age=self.file_cache_max_age,
            )
        if connection_mode == "pull-agent":
            return TCPSource(
                self.host_config.hostname,
                self.ipaddress,
                id_="agent",
                main_data_source=main_data_source,
                simulation_mode=self.simulation_mode,
                agent_simulator=self.agent_simulator,
                translation=self.translation,
                encoding_fallback=self.encoding_fallback,
                check_interval=self.host_config.check_mk_check_interval,
                address_family=self.host_config.default_address_family,
                agent_port=self.host_config.agent_port,
                tcp_connect_timeout=self.host_config.tcp_connect_timeout,
                agent_encryption=self.host_config.agent_encryption,
                file_cache_max_age=self.file_cache_max_age,
            )
        raise NotImplementedError(f"connection mode {connection_mode!r}")

    def _get_special_agents(self) -> Sequence[Source]:
        return [
            SpecialAgentSource(
                self.host_config.hostname,
                self.ipaddress,
                id_=f"special_{agentname}",
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
                check_interval=self.host_config.check_mk_check_interval,
                is_cmc=config.is_cmc(),
                file_cache_max_age=self.file_cache_max_age,
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
    file_cache_max_age: file_cache.MaxAge,
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
        file_cache_max_age=file_cache_max_age,
    ).sources


def fetch_all(
    sources: Iterable[Source],
    *,
    mode: Mode,
) -> Sequence[Tuple[Source, FetcherMessage]]:
    console.verbose("%s+%s %s\n", tty.yellow, tty.normal, "Fetching data".upper())
    out: List[Tuple[Source, FetcherMessage]] = []
    for source in sources:
        console.vverbose("  Source: %s/%s\n" % (source.source_type, source.fetcher_type))

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
    file_cache_max_age: file_cache.MaxAge,
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
            file_cache_max_age=file_cache_max_age,
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
    file_cache_max_age: file_cache.MaxAge,
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
            file_cache_max_age=file_cache_max_age,
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
            file_cache_max_age=file_cache_max_age,
        )
    )
