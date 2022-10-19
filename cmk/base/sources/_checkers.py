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
    overload,
    Sequence,
    Tuple,
)

import cmk.utils.paths
import cmk.utils.tty as tty
from cmk.utils.cpu_tracking import CPUTracker
from cmk.utils.exceptions import OnError
from cmk.utils.log import console
from cmk.utils.type_defs import HostAddress, HostName, result, SectionName, SourceType

from cmk.snmplib.type_defs import (
    BackendSNMPTree,
    SNMPDetectSpec,
    SNMPRawData,
    SNMPRawDataSection,
    TRawData,
)

from cmk.core_helpers import Fetcher, FetcherType, FileCache, get_raw_data, NoFetcher, Parser
from cmk.core_helpers.agent import AgentFileCache, AgentParser, AgentRawData, AgentRawDataSection
from cmk.core_helpers.cache import FileCacheGlobals, FileCacheMode, MaxAge, SectionStore
from cmk.core_helpers.config import AgentParserConfig, SNMPParserConfig
from cmk.core_helpers.host_sections import HostSections, TRawDataSection
from cmk.core_helpers.ipmi import IPMIFetcher
from cmk.core_helpers.piggyback import PiggybackFetcher
from cmk.core_helpers.program import ProgramFetcher
from cmk.core_helpers.protocol import FetcherMessage
from cmk.core_helpers.snmp import (
    SectionMeta,
    SNMPFetcher,
    SNMPFileCache,
    SNMPParser,
    SNMPPluginStore,
    SNMPPluginStoreItem,
)
from cmk.core_helpers.tcp import TCPFetcher
from cmk.core_helpers.type_defs import HostMeta, Mode, NO_SELECTION, SectionNameCollection

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.check_table as check_table
import cmk.base.config as config
import cmk.base.core_config as core_config
from cmk.base.config import HostConfig

__all__ = [
    "fetch_all",
    "make_non_cluster_sources",
    "make_sources",
    "parse",
]


@overload
def parse(
    raw_data: result.Result[AgentRawData, Exception],
    *,
    hostname: HostName,
    fetcher_type: FetcherType,
    ident: str,
    selection: SectionNameCollection,
    logger: logging.Logger,
) -> result.Result[HostSections[AgentRawDataSection], Exception]:
    ...


@overload
def parse(
    raw_data: result.Result[SNMPRawData, Exception],
    *,
    hostname: HostName,
    fetcher_type: FetcherType,
    ident: str,
    selection: SectionNameCollection,
    logger: logging.Logger,
) -> result.Result[HostSections[SNMPRawDataSection], Exception]:
    ...


def parse(
    raw_data: result.Result[TRawData, Exception],
    *,
    hostname: HostName,
    fetcher_type: FetcherType,
    ident: str,
    selection: SectionNameCollection,
    logger: logging.Logger,
) -> result.Result[HostSections[TRawDataSection], Exception]:
    parser = _make_parser(
        hostname,
        fetcher_type=fetcher_type,
        ident=ident,
        logger=logger,
    )
    try:
        return raw_data.map(partial(parser.parse, selection=selection))
    except Exception as exc:
        return result.Error(exc)


def _make_parser(
    hostname: HostName, *, fetcher_type: FetcherType, ident: str, logger: logging.Logger
) -> Parser:
    if fetcher_type is FetcherType.SNMP:
        return SNMPParser(
            hostname,
            SectionStore[SNMPRawDataSection](
                make_persisted_section_dir(fetcher_type=fetcher_type, ident=ident) / hostname,
                logger=logger,
            ),
            **_make_snmp_parser_config(hostname)._asdict(),
            logger=logger,
        )

    agent_parser_config = _make_agent_parser_config(hostname)
    return AgentParser(
        hostname,
        SectionStore[AgentRawDataSection](
            make_persisted_section_dir(fetcher_type=fetcher_type, ident=ident) / hostname,
            logger=logger,
        ),
        check_interval=agent_parser_config.check_interval,
        keep_outdated=agent_parser_config.keep_outdated,
        translation=agent_parser_config.translation,
        encoding_fallback=agent_parser_config.encoding_fallback,
        simulation=agent_parser_config.agent_simulator,  # name mismatch
        logger=logger,
    )


def make_persisted_section_dir(
    *,
    fetcher_type: FetcherType,
    ident: str,
) -> Path:
    var_dir: Final = Path(cmk.utils.paths.var_dir)
    return {
        FetcherType.PIGGYBACK: var_dir / "persisted_sections" / ident,
        FetcherType.SNMP: var_dir / "persisted_sections" / ident,
        FetcherType.IPMI: var_dir / "persisted_sections" / ident,
        FetcherType.PROGRAM: var_dir / "persisted",
        FetcherType.PUSH_AGENT: var_dir / "persisted_sections" / ident,
        FetcherType.TCP: var_dir / "persisted",
    }[fetcher_type]


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
        FetcherType.PROGRAM: os.path.join(base_dir, ident, "{hostname}"),
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
        check_intervals=make_check_intervals(host_config, selected_sections=NO_SELECTION),
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
        missing_sys_description: bool,
        file_cache_max_age: MaxAge,
    ) -> None:
        super().__init__()
        self.host_config: Final = host_config
        self.ipaddress: Final = ipaddress
        self.selected_sections: Final = selected_sections
        self.on_scan_error: Final = on_scan_error
        self.force_snmp_cache_refresh: Final = force_snmp_cache_refresh
        self.simulation_mode: Final = simulation_mode
        self.missing_sys_description: Final = missing_sys_description
        self.file_cache_max_age: Final = file_cache_max_age
        self._elems: Dict[str, Tuple[HostMeta, FileCache, Fetcher]] = {}

        self._initialize()

    @property
    def sources(self) -> Sequence[Tuple[HostMeta, FileCache, Fetcher]]:
        # Always execute piggyback at the end
        return sorted(
            self._elems.values(),
            key=lambda args: (
                args[0].fetcher_type is FetcherType.PIGGYBACK,
                args[0].ident,
            ),
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
            meta = HostMeta(
                self.host_config.hostname,
                self.ipaddress,
                "piggyback",
                FetcherType.PIGGYBACK,
                SourceType.HOST,
            )
            self._add(
                meta,
                PiggybackFetcher(
                    ident=meta.ident,
                    hostname=meta.hostname,
                    address=meta.ipaddress,
                    time_settings=config.get_config_cache().get_piggybacked_hosts_time_settings(
                        piggybacked_hostname=self.host_config.hostname
                    ),
                ),
                AgentFileCache(
                    meta.hostname,
                    path_template=make_file_cache_path_template(
                        fetcher_type=meta.fetcher_type, ident=meta.ident
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
        meta = HostMeta(
            self.host_config.hostname,
            self.ipaddress,
            "snmp",
            FetcherType.SNMP,
            SourceType.HOST,
        )
        self._add(
            meta,
            SNMPFetcher(
                ident=meta.ident,
                sections=make_sections(
                    self.host_config,
                    selected_sections=self.selected_sections,
                ),
                on_error=self.on_scan_error,
                missing_sys_description=self.missing_sys_description,
                do_status_data_inventory=self.host_config.do_status_data_inventory,
                section_store_path=make_persisted_section_dir(
                    fetcher_type=meta.fetcher_type, ident=meta.ident
                )
                / meta.hostname,
                snmp_config=self.host_config.snmp_config(meta.ipaddress),
            ),
            SNMPFileCache(
                meta.hostname,
                path_template=make_file_cache_path_template(
                    fetcher_type=meta.fetcher_type, ident=meta.ident
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
            meta = HostMeta(
                self.host_config.hostname,
                self.ipaddress,
                "mgmt_snmp",
                FetcherType.SNMP,
                SourceType.MANAGEMENT,
            )
            self._add(
                meta,
                SNMPFetcher(
                    ident=meta.ident,
                    sections=make_sections(
                        self.host_config, selected_sections=self.selected_sections
                    ),
                    on_error=self.on_scan_error,
                    missing_sys_description=self.missing_sys_description,
                    do_status_data_inventory=self.host_config.do_status_data_inventory,
                    section_store_path=make_persisted_section_dir(
                        fetcher_type=meta.fetcher_type, ident=meta.ident
                    )
                    / meta.hostname,
                    snmp_config=self.host_config.snmp_config(meta.ipaddress),
                ),
                SNMPFileCache(
                    meta.hostname,
                    path_template=make_file_cache_path_template(
                        fetcher_type=meta.fetcher_type, ident=meta.ident
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
            meta = HostMeta(
                self.host_config.hostname,
                ip_address,
                "mgmt_ipmi",
                FetcherType.IPMI,
                SourceType.MANAGEMENT,
            )
            assert meta.ipaddress
            self._add(
                meta,
                IPMIFetcher(
                    ident=meta.ident,
                    address=meta.ipaddress,
                    username=self.host_config.ipmi_credentials.get("username"),
                    password=self.host_config.ipmi_credentials.get("password"),
                ),
                AgentFileCache(
                    meta.hostname,
                    path_template=make_file_cache_path_template(
                        fetcher_type=meta.fetcher_type, ident=meta.ident
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

    def _add(self, meta: HostMeta, fetcher: Fetcher, file_cache: FileCache) -> None:
        self._elems[meta.ident] = (
            meta,
            file_cache,
            fetcher,
        )

    def _get_agent(self) -> Tuple[HostMeta, Fetcher, FileCache]:
        datasource_program = self.host_config.datasource_program
        if datasource_program is not None:
            meta = HostMeta(
                self.host_config.hostname,
                self.ipaddress,
                "agent",
                FetcherType.PROGRAM,
                SourceType.HOST,
            )
            return (
                meta,
                ProgramFetcher(
                    ident=meta.ident,
                    cmdline=core_config.translate_ds_program_source_cmdline(
                        datasource_program, self.host_config, self.ipaddress
                    ),
                    stdin=None,
                    is_cmc=config.is_cmc(),
                ),
                AgentFileCache(
                    meta.hostname,
                    path_template=make_file_cache_path_template(
                        fetcher_type=meta.fetcher_type, ident=meta.ident
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
            meta = HostMeta(
                self.host_config.hostname,
                self.ipaddress,
                "push-agent",
                FetcherType.PUSH_AGENT,
                SourceType.HOST,
            )
            # convert to seconds and add grace period
            interval = int(1.5 * 60 * self.host_config.check_mk_check_interval)
            return (
                meta,
                NoFetcher(),
                AgentFileCache(
                    meta.hostname,
                    path_template=make_file_cache_path_template(
                        fetcher_type=meta.fetcher_type, ident=meta.ident
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
            meta = HostMeta(
                self.host_config.hostname,
                self.ipaddress,
                "agent",
                FetcherType.TCP,
                SourceType.HOST,
            )
            return (
                meta,
                TCPFetcher(
                    ident=meta.ident,
                    family=self.host_config.default_address_family,
                    address=(meta.ipaddress, self.host_config.agent_port),
                    host_name=meta.hostname,
                    timeout=self.host_config.tcp_connect_timeout,
                    encryption_settings=self.host_config.agent_encryption,
                ),
                AgentFileCache(
                    meta.hostname,
                    path_template=make_file_cache_path_template(
                        fetcher_type=meta.fetcher_type, ident=meta.ident
                    ),
                    max_age=self.file_cache_max_age,
                    use_outdated=self.simulation_mode or FileCacheGlobals.use_outdated,
                    simulation=self.simulation_mode,
                    use_only_cache=FileCacheGlobals.tcp_use_only_cache,
                    file_cache_mode=FileCacheGlobals.file_cache_mode(),
                ),
            )
        raise NotImplementedError(f"connection mode {connection_mode!r}")

    def _get_special_agents(self) -> Iterable[Tuple[HostMeta, Fetcher, FileCache]]:
        def make_id(agentname: str) -> str:
            return f"special_{agentname}"

        for agentname, params in self.host_config.special_agents:
            meta = HostMeta(
                self.host_config.hostname,
                self.ipaddress,
                make_id(agentname),
                FetcherType.PROGRAM,
                SourceType.HOST,
            )
            fetcher = ProgramFetcher(
                ident=meta.ident,
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
                is_cmc=config.is_cmc(),
            )
            file_cache = AgentFileCache(
                meta.hostname,
                path_template=make_file_cache_path_template(
                    fetcher_type=meta.fetcher_type, ident=meta.ident
                ),
                max_age=self.file_cache_max_age,
                use_outdated=self.simulation_mode or FileCacheGlobals.use_outdated,
                simulation=self.simulation_mode,
                use_only_cache=False,
                file_cache_mode=FileCacheGlobals.file_cache_mode(),
            )
            yield meta, fetcher, file_cache


def make_non_cluster_sources(
    host_config: HostConfig,
    ipaddress: Optional[HostAddress],
    *,
    force_snmp_cache_refresh: bool = False,
    selected_sections: SectionNameCollection = NO_SELECTION,
    on_scan_error: OnError = OnError.RAISE,
    simulation_mode: bool,
    missing_sys_description: bool,
    file_cache_max_age: MaxAge,
) -> Sequence[Tuple[HostMeta, FileCache, Fetcher]]:
    """Sequence of sources available for `host_config`."""
    return _Builder(
        host_config,
        ipaddress,
        selected_sections=selected_sections,
        on_scan_error=on_scan_error,
        force_snmp_cache_refresh=force_snmp_cache_refresh,
        simulation_mode=simulation_mode,
        missing_sys_description=missing_sys_description,
        file_cache_max_age=file_cache_max_age,
    ).sources


def fetch_all(
    sources: Iterable[Tuple[HostMeta, FileCache, Fetcher]],
    *,
    mode: Mode,
) -> Sequence[Tuple[HostMeta, FetcherMessage]]:
    console.verbose("%s+%s %s\n", tty.yellow, tty.normal, "Fetching data".upper())
    out: List[Tuple[HostMeta, FetcherMessage]] = []
    for meta, file_cache, fetcher in sources:
        console.vverbose("  Source: %s\n" % (meta,))

        with CPUTracker() as tracker:
            raw_data = get_raw_data(file_cache, fetcher, mode)
        out.append(
            (
                meta,
                FetcherMessage.from_raw_data(
                    meta.hostname,
                    meta.ident,
                    raw_data,
                    tracker.duration,
                    meta.fetcher_type,
                    meta.source_type,
                ),
            )
        )
    return out


def make_sources(
    host_config: HostConfig,
    ip_address: Optional[HostAddress],
    *,
    ip_lookup: Callable[[HostName], Optional[HostAddress]],
    selected_sections: SectionNameCollection,
    force_snmp_cache_refresh: bool,
    on_scan_error: OnError,
    simulation_mode: bool,
    missing_sys_description: bool,
    file_cache_max_age: MaxAge,
) -> Sequence[Tuple[HostMeta, FileCache, Fetcher]]:
    if host_config.nodes is None:
        # Not a cluster
        host_configs = [host_config]
    else:
        host_configs = [HostConfig.make_host_config(host_name) for host_name in host_config.nodes]
    return [
        source
        for host_config_ in host_configs
        for source in make_non_cluster_sources(
            host_config_,
            ip_address if host_config.nodes is None else ip_lookup(host_config_.hostname),
            force_snmp_cache_refresh=force_snmp_cache_refresh
            if host_config.nodes is None
            else False,
            selected_sections=selected_sections if host_config.nodes is None else NO_SELECTION,
            on_scan_error=on_scan_error if host_config.nodes is None else OnError.RAISE,
            simulation_mode=simulation_mode,
            missing_sys_description=missing_sys_description,
            file_cache_max_age=file_cache_max_age,
        )
    ]
