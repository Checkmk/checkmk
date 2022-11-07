#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO: Cluster with different data sources, eg. TCP node and SNMP node:
# - Discovery works.
# - Checking doesn't work - as it was before. Maybe we can handle this in the future.

import logging
import os.path
from functools import partial
from pathlib import Path
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

import cmk.utils.paths
import cmk.utils.tty as tty
from cmk.utils.cpu_tracking import CPUTracker, Snapshot
from cmk.utils.exceptions import OnError
from cmk.utils.log import console
from cmk.utils.type_defs import HostAddress, HostName, result, SectionName, SourceType

from cmk.snmplib.type_defs import BackendSNMPTree, SNMPDetectSpec, SNMPRawData, SNMPRawDataSection

from cmk.core_helpers import Fetcher, FetcherType, FileCache, get_raw_data, NoFetcher, Parser
from cmk.core_helpers.agent import AgentFileCache, AgentParser, AgentRawData, AgentRawDataSection
from cmk.core_helpers.cache import FileCacheGlobals, FileCacheMode, MaxAge, SectionStore
from cmk.core_helpers.config import AgentParserConfig, SNMPParserConfig
from cmk.core_helpers.host_sections import HostSections
from cmk.core_helpers.ipmi import IPMIFetcher
from cmk.core_helpers.piggyback import PiggybackFetcher
from cmk.core_helpers.program import ProgramFetcher
from cmk.core_helpers.snmp import (
    SectionMeta,
    SNMPFetcher,
    SNMPFileCache,
    SNMPParser,
    SNMPPluginStore,
    SNMPPluginStoreItem,
)
from cmk.core_helpers.tcp import TCPFetcher
from cmk.core_helpers.type_defs import Mode, NO_SELECTION, SectionNameCollection, SourceInfo

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.check_table as check_table
import cmk.base.config as config
import cmk.base.core_config as core_config
from cmk.base.config import HostConfig

__all__ = [
    "fetch_all",
    "make_non_cluster_sources",
    "make_sources",
    "make_plugin_store",
    "parse",
]


def parse(
    source: SourceInfo,
    raw_data: result.Result[AgentRawData | SNMPRawData, Exception],
    *,
    selection: SectionNameCollection,
    logger: logging.Logger,
) -> result.Result[HostSections[AgentRawDataSection | SNMPRawDataSection], Exception]:
    parser = _make_parser(source, logger=logger)
    try:
        return raw_data.map(partial(parser.parse, selection=selection))
    except Exception as exc:
        return result.Error(exc)


def _make_parser(source: SourceInfo, *, logger: logging.Logger) -> Parser:
    if source.fetcher_type is FetcherType.SNMP:
        return SNMPParser(
            source.hostname,
            SectionStore[SNMPRawDataSection](make_persisted_section_dir(source), logger=logger),
            **_make_snmp_parser_config(source.hostname)._asdict(),
            logger=logger,
        )

    agent_parser_config = _make_agent_parser_config(source.hostname)
    return AgentParser(
        source.hostname,
        SectionStore[AgentRawDataSection](make_persisted_section_dir(source), logger=logger),
        check_interval=agent_parser_config.check_interval,
        keep_outdated=agent_parser_config.keep_outdated,
        translation=agent_parser_config.translation,
        encoding_fallback=agent_parser_config.encoding_fallback,
        simulation=agent_parser_config.agent_simulator,  # name mismatch
        logger=logger,
    )


def make_persisted_section_dir(source: SourceInfo) -> Path:
    var_dir: Final = Path(cmk.utils.paths.var_dir)
    return {
        FetcherType.PIGGYBACK: var_dir / "persisted_sections" / source.ident / str(source.hostname),
        FetcherType.SNMP: var_dir / "persisted_sections" / source.ident / str(source.hostname),
        FetcherType.IPMI: var_dir / "persisted_sections" / source.ident / str(source.hostname),
        FetcherType.PROGRAM: var_dir / "persisted" / str(source.hostname),
        FetcherType.SPECIAL_AGENT: var_dir
        / "persisted_sections"
        / source.ident
        / str(source.hostname),
        FetcherType.PUSH_AGENT: var_dir
        / "persisted_sections"
        / source.ident
        / str(source.hostname),
        FetcherType.TCP: var_dir / "persisted" / str(source.hostname),
    }[source.fetcher_type]


def make_file_cache_path_template(
    *,
    fetcher_type: FetcherType,
    ident: str,
) -> str:
    # We create a *template* and not a path, so string manipulation
    # is the right thing to do.
    base_dir: Final = str(cmk.utils.paths.data_source_cache_dir)
    return {
        FetcherType.PIGGYBACK: os.path.join(base_dir, ident, "{hostname}"),
        FetcherType.SNMP: os.path.join(base_dir, ident, "{mode}", "{hostname}"),
        FetcherType.IPMI: os.path.join(base_dir, ident, "{hostname}"),
        FetcherType.SPECIAL_AGENT: os.path.join(base_dir, ident, "{hostname}"),
        FetcherType.PROGRAM: os.path.join(cmk.utils.paths.tcp_cache_dir, "{hostname}"),
        FetcherType.PUSH_AGENT: os.path.join(base_dir, ident, "{hostname}", "agent_output"),
        FetcherType.TCP: os.path.join(cmk.utils.paths.tcp_cache_dir, "{hostname}"),
    }[fetcher_type]


def _make_agent_parser_config(hostname: HostName) -> AgentParserConfig:
    # Move to `cmk.base.config` once the direction of the dependencies
    # has been fixed (ie, as little components as possible get the full,
    # global config instead of whatever they need to work).
    host_config = HostConfig.make_host_config(hostname)
    return AgentParserConfig(
        check_interval=host_config.check_mk_check_interval,
        encoding_fallback=config.fallback_agent_output_encoding,
        keep_outdated=FileCacheGlobals.keep_outdated,
        translation=config.get_piggyback_translations(hostname),
        agent_simulator=config.agent_simulator,
    )


def _make_snmp_parser_config(hostname: HostName) -> SNMPParserConfig:
    # Move to `cmk.base.config` once the direction of the dependencies
    # has been fixed (ie, as little components as possible get the full,
    # global config instead of whatever they need to work).
    host_config = HostConfig.make_host_config(hostname)
    return SNMPParserConfig(
        check_intervals=make_check_intervals(hostname, host_config, selected_sections=NO_SELECTION),
        keep_outdated=FileCacheGlobals.keep_outdated,
    )


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
    host_name: HostName,
    host_config: HostConfig,
    *,
    selected_sections: SectionNameCollection,
) -> Mapping[SectionName, Optional[int]]:
    return {
        section_name: host_config.snmp_fetch_interval(section_name)
        for section_name in _make_checking_sections(host_name, selected_sections=selected_sections)
    }


def make_sections(
    host_name: HostName,
    host_config: HostConfig,
    *,
    selected_sections: SectionNameCollection,
) -> Dict[SectionName, SectionMeta]:
    def needs_redetection(section_name: SectionName) -> bool:
        section = agent_based_register.get_section_plugin(section_name)
        return len(agent_based_register.get_section_producers(section.parsed_section_name)) > 1

    checking_sections = _make_checking_sections(host_name, selected_sections=selected_sections)
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
        host_name: HostName,
        ipaddress: Optional[HostAddress],
        *,
        selected_sections: SectionNameCollection,
        on_scan_error: OnError,
        force_snmp_cache_refresh: bool,
        simulation_mode: bool,
        missing_sys_description: bool,
        file_cache_max_age: MaxAge,
    ) -> None:
        super().__init__()
        self.host_name: Final = host_name
        self.config_cache: Final = config.get_config_cache()
        self.host_config: Final = self.config_cache.get_host_config(self.host_name)
        self.ipaddress: Final = ipaddress
        self.selected_sections: Final = selected_sections
        self.on_scan_error: Final = on_scan_error
        self.force_snmp_cache_refresh: Final = force_snmp_cache_refresh
        self.simulation_mode: Final = simulation_mode
        self.missing_sys_description: Final = missing_sys_description
        self.file_cache_max_age: Final = file_cache_max_age
        self._elems: Dict[str, Tuple[SourceInfo, FileCache, Fetcher]] = {}

        self._initialize()

    @property
    def sources(self) -> Sequence[Tuple[SourceInfo, FileCache, Fetcher]]:
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
        if self.host_config.is_all_agents_host:
            self._add(*self._get_agent())
            for elem in self._get_special_agents():
                self._add(*elem)

        elif self.host_config.is_all_special_agents_host:
            for elem in self._get_special_agents():
                self._add(*elem)

        elif self.host_config.is_tcp_host:
            special_agents = tuple(self._get_special_agents())
            if special_agents:
                self._add(*special_agents[0])
            else:
                self._add(*self._get_agent())

        if "no-piggyback" not in self.host_config.tags:
            source = SourceInfo(
                self.host_name,
                self.ipaddress,
                "piggyback",
                FetcherType.PIGGYBACK,
                SourceType.HOST,
            )
            self._add(
                source,
                PiggybackFetcher(
                    hostname=source.hostname,
                    address=source.ipaddress,
                    time_settings=config.get_config_cache().get_piggybacked_hosts_time_settings(
                        piggybacked_hostname=self.host_name
                    ),
                ),
                AgentFileCache(
                    source.hostname,
                    path_template=make_file_cache_path_template(
                        fetcher_type=source.fetcher_type, ident=source.ident
                    ),
                    max_age=self.file_cache_max_age,
                    use_outdated=FileCacheGlobals.use_outdated,
                    simulation=False,  # TODO Quickfix for SUP-9912
                    use_only_cache=False,
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
        if not self.host_config.is_snmp_host:
            return
        self._initialize_snmp_plugin_store()
        source = SourceInfo(
            self.host_name,
            self.ipaddress,
            "snmp",
            FetcherType.SNMP,
            SourceType.HOST,
        )
        self._add(
            source,
            SNMPFetcher(
                sections=make_sections(
                    self.host_name,
                    self.host_config,
                    selected_sections=self.selected_sections,
                ),
                on_error=self.on_scan_error,
                missing_sys_description=self.missing_sys_description,
                do_status_data_inventory=self.host_config.do_status_data_inventory,
                section_store_path=make_persisted_section_dir(source),
                snmp_config=self.host_config.snmp_config(source.ipaddress),
            ),
            SNMPFileCache(
                source.hostname,
                path_template=make_file_cache_path_template(
                    fetcher_type=source.fetcher_type, ident=source.ident
                ),
                max_age=(
                    MaxAge.none() if self.force_snmp_cache_refresh else self.file_cache_max_age
                ),
                use_outdated=(
                    self.simulation_mode
                    or (False if self.force_snmp_cache_refresh else FileCacheGlobals.use_outdated)
                ),
                simulation=self.simulation_mode,
                use_only_cache=False,
                file_cache_mode=FileCacheGlobals.file_cache_mode(),
            ),
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
            source = SourceInfo(
                self.host_name,
                self.ipaddress,
                "mgmt_snmp",
                FetcherType.SNMP,
                SourceType.MANAGEMENT,
            )
            self._add(
                source,
                SNMPFetcher(
                    sections=make_sections(
                        self.host_name, self.host_config, selected_sections=self.selected_sections
                    ),
                    on_error=self.on_scan_error,
                    missing_sys_description=self.missing_sys_description,
                    do_status_data_inventory=self.host_config.do_status_data_inventory,
                    section_store_path=make_persisted_section_dir(source),
                    snmp_config=self.host_config.snmp_config(source.ipaddress),
                ),
                SNMPFileCache(
                    source.hostname,
                    path_template=make_file_cache_path_template(
                        fetcher_type=source.fetcher_type, ident=source.ident
                    ),
                    max_age=(
                        MaxAge.none() if self.force_snmp_cache_refresh else self.file_cache_max_age
                    ),
                    use_outdated=(
                        self.simulation_mode
                        or (
                            False
                            if self.force_snmp_cache_refresh
                            else FileCacheGlobals.use_outdated
                        )
                    ),
                    simulation=self.simulation_mode,
                    use_only_cache=False,
                    file_cache_mode=FileCacheGlobals.file_cache_mode(),
                ),
            )
        elif protocol == "ipmi":
            source = SourceInfo(
                self.host_name,
                ip_address,
                "mgmt_ipmi",
                FetcherType.IPMI,
                SourceType.MANAGEMENT,
            )
            assert source.ipaddress
            self._add(
                source,
                IPMIFetcher(
                    address=source.ipaddress,
                    username=self.host_config.ipmi_credentials.get("username"),
                    password=self.host_config.ipmi_credentials.get("password"),
                ),
                AgentFileCache(
                    source.hostname,
                    path_template=make_file_cache_path_template(
                        fetcher_type=source.fetcher_type, ident=source.ident
                    ),
                    max_age=self.file_cache_max_age,
                    use_outdated=self.simulation_mode or FileCacheGlobals.use_outdated,
                    simulation=self.simulation_mode,
                    use_only_cache=False,
                    file_cache_mode=FileCacheGlobals.file_cache_mode(),
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

    def _get_agent(self) -> Tuple[SourceInfo, Fetcher, FileCache]:
        datasource_program = self.host_config.datasource_program
        if datasource_program is not None:
            source = SourceInfo(
                self.host_name,
                self.ipaddress,
                "agent",
                FetcherType.PROGRAM,
                SourceType.HOST,
            )
            return (
                source,
                ProgramFetcher(
                    cmdline=core_config.translate_ds_program_source_cmdline(
                        datasource_program, self.host_name, self.host_config, self.ipaddress
                    ),
                    stdin=None,
                    is_cmc=config.is_cmc(),
                ),
                AgentFileCache(
                    source.hostname,
                    path_template=make_file_cache_path_template(
                        fetcher_type=source.fetcher_type, ident=source.ident
                    ),
                    max_age=self.file_cache_max_age,
                    use_outdated=self.simulation_mode or FileCacheGlobals.use_outdated,
                    simulation=self.simulation_mode,
                    use_only_cache=False,
                    file_cache_mode=FileCacheGlobals.file_cache_mode(),
                ),
            )

        connection_mode = self.host_config.agent_connection_mode()
        if connection_mode == "push-agent":
            source = SourceInfo(
                self.host_name,
                self.ipaddress,
                "push-agent",
                FetcherType.PUSH_AGENT,
                SourceType.HOST,
            )
            # convert to seconds and add grace period
            interval = int(1.5 * 60 * self.host_config.check_mk_check_interval)
            return (
                source,
                NoFetcher(),
                AgentFileCache(
                    source.hostname,
                    path_template=make_file_cache_path_template(
                        fetcher_type=source.fetcher_type, ident=source.ident
                    ),
                    max_age=MaxAge(interval, interval, interval),
                    use_outdated=self.simulation_mode or FileCacheGlobals.use_outdated,
                    simulation=self.simulation_mode,
                    use_only_cache=True,
                    file_cache_mode=(
                        # Careful: at most read-only!
                        FileCacheMode.DISABLED
                        if FileCacheGlobals.disabled
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
                TCPFetcher(
                    family=self.host_config.default_address_family,
                    address=(source.ipaddress, self.host_config.agent_port),
                    host_name=source.hostname,
                    timeout=self.host_config.tcp_connect_timeout,
                    encryption_handling=self.host_config.encryption_handling,
                    pre_shared_secret=self.host_config.symmetric_agent_encryption,
                ),
                AgentFileCache(
                    source.hostname,
                    path_template=make_file_cache_path_template(
                        fetcher_type=source.fetcher_type, ident=source.ident
                    ),
                    max_age=self.file_cache_max_age,
                    use_outdated=self.simulation_mode or FileCacheGlobals.use_outdated,
                    simulation=self.simulation_mode,
                    use_only_cache=FileCacheGlobals.tcp_use_only_cache,
                    file_cache_mode=FileCacheGlobals.file_cache_mode(),
                ),
            )
        raise NotImplementedError(f"connection mode {connection_mode!r}")

    def _get_special_agents(self) -> Iterable[Tuple[SourceInfo, Fetcher, FileCache]]:
        def make_id(agentname: str) -> str:
            return f"special_{agentname}"

        for agentname, params in self.host_config.special_agents:
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
                max_age=self.file_cache_max_age,
                use_outdated=self.simulation_mode or FileCacheGlobals.use_outdated,
                simulation=self.simulation_mode,
                use_only_cache=False,
                file_cache_mode=FileCacheGlobals.file_cache_mode(),
            )
            yield source, fetcher, file_cache


def make_non_cluster_sources(
    host_name: HostName,
    ipaddress: Optional[HostAddress],
    *,
    force_snmp_cache_refresh: bool = False,
    selected_sections: SectionNameCollection = NO_SELECTION,
    on_scan_error: OnError = OnError.RAISE,
    simulation_mode: bool,
    missing_sys_description: bool,
    file_cache_max_age: MaxAge,
) -> Sequence[Tuple[SourceInfo, FileCache, Fetcher]]:
    """Sequence of sources available for `host_config`."""
    return _Builder(
        host_name,
        ipaddress,
        selected_sections=selected_sections,
        on_scan_error=on_scan_error,
        force_snmp_cache_refresh=force_snmp_cache_refresh,
        simulation_mode=simulation_mode,
        missing_sys_description=missing_sys_description,
        file_cache_max_age=file_cache_max_age,
    ).sources


def fetch_all(
    sources: Iterable[Tuple[SourceInfo, FileCache, Fetcher]],
    *,
    mode: Mode,
) -> Sequence[Tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception], Snapshot]]:
    console.verbose("%s+%s %s\n", tty.yellow, tty.normal, "Fetching data".upper())
    out: List[
        Tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception], Snapshot]
    ] = []
    for source, file_cache, fetcher in sources:
        console.vverbose("  Source: %s\n" % (source,))

        with CPUTracker() as tracker:
            raw_data = get_raw_data(file_cache, fetcher, mode)
        out.append((source, raw_data, tracker.duration))
    return out


def make_sources(
    host_name: HostName,
    ip_address: Optional[HostAddress],
    *,
    ip_lookup: Callable[[HostName], Optional[HostAddress]],
    selected_sections: SectionNameCollection,
    force_snmp_cache_refresh: bool,
    on_scan_error: OnError,
    simulation_mode: bool,
    missing_sys_description: bool,
    file_cache_max_age: MaxAge,
) -> Sequence[Tuple[SourceInfo, FileCache, Fetcher]]:
    config_cache = config.get_config_cache()
    nodes = config_cache.nodes_of(host_name)
    if nodes is None:
        # Not a cluster
        host_names = [host_name]
    else:
        host_names = nodes
    return [
        source
        for host_name_ in host_names
        for source in make_non_cluster_sources(
            host_name_,
            (ip_address if config_cache.nodes_of(host_name) is None else ip_lookup(host_name_)),
            force_snmp_cache_refresh=(
                force_snmp_cache_refresh if config_cache.nodes_of(host_name) is None else False
            ),
            selected_sections=(
                selected_sections if config_cache.nodes_of(host_name) is None else NO_SELECTION
            ),
            on_scan_error=(
                on_scan_error if config_cache.nodes_of(host_name) is None else OnError.RAISE
            ),
            simulation_mode=simulation_mode,
            missing_sys_description=missing_sys_description,
            file_cache_max_age=file_cache_max_age,
        )
    ]
