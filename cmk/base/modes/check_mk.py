#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import enum
import itertools
import logging
import os
import subprocess
import sys
import time
from collections.abc import Callable, Container, Iterable, Mapping, Sequence
from contextlib import suppress
from pathlib import Path
from typing import Final, Literal, NamedTuple, TypedDict, TypeVar

import livestatus

import cmk.ccc.cleanup
import cmk.ccc.debug
import cmk.ccc.version as cmk_version
from cmk.ccc import store, tty
from cmk.ccc.cpu_tracking import CPUTracker
from cmk.ccc.exceptions import MKBailOut, MKGeneralException, MKTimeout, OnError
from cmk.ccc.hostaddress import HostAddress, HostName, Hosts

import cmk.utils.password_store
import cmk.utils.paths
from cmk.utils import config_warnings, ip_lookup, log
from cmk.utils.auto_queue import AutoQueue
from cmk.utils.check_utils import maincheckify
from cmk.utils.diagnostics import (
    DiagnosticsModesParameters,
    OPT_CHECKMK_CONFIG_FILES,
    OPT_CHECKMK_LOG_FILES,
    OPT_CHECKMK_OVERVIEW,
    OPT_LOCAL_FILES,
    OPT_OMD_CONFIG,
    OPT_PERFORMANCE_GRAPHS,
)
from cmk.utils.everythingtype import EVERYTHING
from cmk.utils.ip_lookup import ConfiguredIPLookup
from cmk.utils.log import console, section
from cmk.utils.paths import configuration_lockfile
from cmk.utils.rulesets.tuple_rulesets import hosttags_match_taglist
from cmk.utils.sectionname import SectionMap, SectionName
from cmk.utils.servicename import ServiceName
from cmk.utils.structured_data import (
    ImmutableTree,
    InventoryPaths,
    InventoryStore,
    make_meta,
    MutableTree,
    RawIntervalFromConfig,
    UpdateResult,
)
from cmk.utils.tags import TagID
from cmk.utils.timeout import Timeout
from cmk.utils.timeperiod import load_timeperiods

from cmk.snmplib import (
    get_single_oid,
    OID,
    oids_to_walk,
    SNMPBackend,
    SNMPBackendEnum,
    walk_for_export,
)

import cmk.fetchers.snmp as snmp_factory
from cmk.fetchers import get_raw_data, SNMPScanConfig, TLSConfig
from cmk.fetchers import Mode as FetchMode
from cmk.fetchers.config import make_persisted_section_dir
from cmk.fetchers.filecache import FileCacheOptions, MaxAge

from cmk.checkengine import inventory
from cmk.checkengine.checking import (
    execute_checkmk_checks,
    make_timing_results,
)
from cmk.checkengine.checkresults import ActiveCheckResult
from cmk.checkengine.discovery import (
    commandline_discovery,
    execute_check_discovery,
    remove_autochecks_of_host,
)
from cmk.checkengine.fetcher import FetcherFunction, FetcherType, SourceType
from cmk.checkengine.inventory import HWSWInventoryParameters
from cmk.checkengine.parser import (
    NO_SELECTION,
    parse_raw_data,
    ParserFunction,
    SectionNameCollection,
)
from cmk.checkengine.plugin_backend import (
    extract_known_discovery_rulesets,
    filter_relevant_raw_sections,
)
from cmk.checkengine.plugins import (
    AgentBasedPlugins,
    AgentSectionPlugin,
    CheckPlugin,
    CheckPluginName,
    InventoryPlugin,
    InventoryPluginName,
    SNMPSectionPlugin,
)
from cmk.checkengine.sectionparser import SectionPlugin
from cmk.checkengine.submitters import get_submitter, ServiceState
from cmk.checkengine.summarize import summarize, SummarizerFunction
from cmk.checkengine.value_store import AllValueStoresStore, ValueStoreManager

import cmk.base.core
import cmk.base.core_nagios
import cmk.base.diagnostics
import cmk.base.dump_host
import cmk.base.parent_scan
from cmk.base import config, profiling, sources
from cmk.base.checkers import (
    CheckerPluginMapper,
    CMKFetcher,
    CMKParser,
    CMKSummarizer,
    DiscoveryPluginMapper,
    HostLabelPluginMapper,
    SectionPluginMapper,
)
from cmk.base.config import (
    ConfigCache,
    handle_ip_lookup_failure,
)
from cmk.base.configlib.checkengine import DiscoveryConfig
from cmk.base.core_factory import create_core, get_licensing_handler_type
from cmk.base.errorhandling import CheckResultErrorHandler, create_section_crash_dump
from cmk.base.modes import Mode, modes, Option
from cmk.base.sources import make_parser, SNMPFetcherConfig
from cmk.base.utils import register_sigint_handler

from cmk import trace
from cmk.agent_based.v1.value_store import set_value_store_manager
from cmk.discover_plugins import discover_families, PluginGroup
from cmk.piggyback import backend as piggyback_backend
from cmk.server_side_calls_backend import load_active_checks

from ._localize import do_localize

tracer = trace.get_tracer()


def load_config(plugins: AgentBasedPlugins) -> config.LoadingResult:
    # Read the configuration files (main.mk, autochecks, etc.), but not for
    # certain operation modes that does not need them and should not be harmed
    # by a broken configuration
    return config.load(discovery_rulesets=extract_known_discovery_rulesets(plugins))


def load_checks() -> AgentBasedPlugins:
    plugins = config.load_all_pluginX(cmk.utils.paths.checks_dir)
    if sys.stderr.isatty():
        for error_msg in plugins.errors:
            console.error(error_msg, file=sys.stderr)
    return plugins


# .
#   .--General options-----------------------------------------------------.
#   |       ____                           _               _               |
#   |      / ___| ___ _ __   ___ _ __ __ _| |   ___  _ __ | |_ ___         |
#   |     | |  _ / _ \ '_ \ / _ \ '__/ _` | |  / _ \| '_ \| __/ __|        |
#   |     | |_| |  __/ | | |  __/ | | (_| | | | (_) | |_) | |_\__ \_       |
#   |      \____|\___|_| |_|\___|_|  \__,_|_|  \___/| .__/ \__|___(_)      |
#   |                                               |_|                    |
#   +----------------------------------------------------------------------+
#   | The general options that are available for all Checkmk modes. Only   |
#   | add new general options in case they are really affecting basic      |
#   | things and used by the most of the modes.                            |
#   '----------------------------------------------------------------------'

_verbosity = 0


def print_(txt: str) -> None:
    with suppress(IOError):
        sys.stdout.write(txt)
        sys.stdout.flush()


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


def option_verbosity() -> None:
    global _verbosity
    _verbosity += 1
    log.logger.setLevel(log.verbosity_to_log_level(_verbosity))


modes.register_general_option(
    Option(
        long_option="verbose",
        short_option="v",
        short_help="Enable verbose output (Use twice for more)",
        handler_function=option_verbosity,
    )
)


def option_debug() -> None:
    cmk.ccc.debug.enable()


modes.register_general_option(
    Option(
        long_option="debug",
        short_help="Let most Python exceptions raise through",
        handler_function=option_debug,
    )
)


def option_profile() -> None:
    profiling.enable()


modes.register_general_option(
    Option(
        long_option="profile",
        short_help="Enable profiling mode",
        handler_function=option_profile,
    )
)


def option_fake_dns(a: HostAddress) -> None:
    ip_lookup.enforce_fake_dns(a)


modes.register_general_option(
    Option(
        long_option="fake-dns",
        short_help="Fake IP addresses of all hosts to be IP. This prevents DNS lookups.",
        handler_function=option_fake_dns,
        argument=True,
        argument_descr="IP",
    )
)


# .
#   .--Fetcher options-----------------------------------------------------.
#   |                  _____    _       _                                  |
#   |                 |  ___|__| |_ ___| |__   ___ _ __                    |
#   |                 | |_ / _ \ __/ __| '_ \ / _ \ '__|                   |
#   |                 |  _|  __/ || (__| | | |  __/ |                      |
#   |                 |_|  \___|\__\___|_| |_|\___|_|                      |
#   |                                                                      |
#   |                              _   _                                   |
#   |                   ___  _ __ | |_(_) ___  _ __  ___                   |
#   |                  / _ \| '_ \| __| |/ _ \| '_ \/ __|                  |
#   |                 | (_) | |_) | |_| | (_) | | | \__ \                  |
#   |                  \___/| .__/ \__|_|\___/|_| |_|___/                  |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+
#   | These options are shared by all modes that use fetchers.             |
#   | These used to be general options, that's why we currently have these |
#   | handler *like*  functions, that only have side-effects.              |
#   | It's not meant to stay this way.                                     |
#   '----------------------------------------------------------------------'
# .


def _handle_fetcher_options(
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
        file_cache_options = dataclasses.replace(file_cache_options, tcp_use_only_cache=True)

    if options.get("usewalk", False):
        snmp_factory.force_stored_walks()
        ip_lookup.enforce_localhost()

    return file_cache_options


_FETCHER_OPTIONS: Final = [
    Option(
        long_option="cache",
        short_help="Read info from data source cache files when existent, even when it "
        "is outdated. Only contact the data sources when the cache file "
        "is absent",
    ),
    Option(
        long_option="no-cache",
        short_help="Never use cached information",
    ),
    Option(
        long_option="no-tcp",
        short_help="Only use cache files. Skip hosts without cache files.",
    ),
    Option(
        long_option="usewalk",
        short_help="Use snmpwalk stored with --snmpwalk",
    ),
]

_SNMP_BACKEND_OPTION: Final = Option(
    long_option="snmp-backend",
    short_help="Override default SNMP backend",
    argument=True,
    argument_descr="inline|classic|stored-walk",
)

# .
#   .--list-hosts----------------------------------------------------------.
#   |              _ _     _        _               _                      |
#   |             | (_)___| |_     | |__   ___  ___| |_ ___                |
#   |             | | / __| __|____| '_ \ / _ \/ __| __/ __|               |
#   |             | | \__ \ ||_____| | | | (_) \__ \ |_\__ \               |
#   |             |_|_|___/\__|    |_| |_|\___/|___/\__|___/               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def mode_list_hosts(options: dict, args: list[str]) -> None:
    config_cache = config.load(discovery_rulesets=()).config_cache
    hosts = _list_all_hosts(
        config_cache,
        args,
        options,
    )
    with suppress(IOError):
        sys.stdout.write("\n".join(hosts) + "\n")
        sys.stdout.flush()


# TODO: Does not care about internal group "check_mk"
def _list_all_hosts(
    config_cache: ConfigCache,
    hostgroups: list[str],
    options: dict,
) -> list[HostName]:
    hosts_config = config_cache.hosts_config
    hostnames: Iterable[HostName]

    all_sites = options.get("all-sites")
    offline = "include-offline" in options

    if all_sites:
        hostnames = filter(
            lambda hn: offline or config_cache.is_online(hn),
            itertools.chain(hosts_config.hosts, hosts_config.clusters, hosts_config.shadow_hosts),
        )
    else:
        hostnames = filter(
            lambda hn: config_cache.is_active(hn) and (offline or config_cache.is_online(hn)),
            itertools.chain(hosts_config.hosts, hosts_config.clusters),
        )

    hostnames = sorted(set(hostnames))
    if not hostgroups:
        return hostnames

    hostlist = []
    for hn in hostnames:
        for hg in config_cache.hostgroups(hn):
            if hg in hostgroups:
                hostlist.append(hn)
                break

    return hostlist


modes.register(
    Mode(
        long_option="list-hosts",
        short_option="l",
        handler_function=mode_list_hosts,
        argument=True,
        argument_descr="G1 G2...",
        argument_optional=True,
        short_help="Print list of all hosts or members of host groups",
        long_help=[
            "Called without argument lists all hosts. You may "
            "specify one or more host groups to restrict the output to hosts "
            "that are in at least one of those groups.",
        ],
        sub_options=[
            Option(
                long_option="all-sites",
                short_help="Include hosts of foreign sites",
            ),
            Option(
                long_option="include-offline",
                short_help="Include offline hosts",
            ),
        ],
    )
)

# .
#   .--list-tag------------------------------------------------------------.
#   |                   _ _     _        _                                 |
#   |                  | (_)___| |_     | |_ __ _  __ _                    |
#   |                  | | / __| __|____| __/ _` |/ _` |                   |
#   |                  | | \__ \ ||_____| || (_| | (_| |                   |
#   |                  |_|_|___/\__|     \__\__,_|\__, |                   |
#   |                                             |___/                    |
#   '----------------------------------------------------------------------'


def mode_list_tag(args: list[str]) -> None:
    config_cache = config.load(discovery_rulesets=()).config_cache
    hosts = _list_all_hosts_with_tags(tuple(TagID(_) for _ in args), config_cache)
    print_("\n".join(sorted(hosts)))
    if hosts:
        print_("\n")


def _list_all_hosts_with_tags(
    tags: Sequence[TagID], config_cache: ConfigCache
) -> Sequence[HostName]:
    hosts_config = config_cache.hosts_config

    if "offline" in tags:
        hostnames = filter(
            lambda hn: config_cache.is_active(hn) and config_cache.is_offline(hn),
            itertools.chain(hosts_config.hosts, hosts_config.clusters),
        )
    else:
        hostnames = filter(
            lambda hn: config_cache.is_active(hn) and config_cache.is_online(hn),
            itertools.chain(hosts_config.hosts, hosts_config.clusters),
        )

    hosts = []
    for h in set(hostnames):
        if hosttags_match_taglist(config_cache.host_tags.tag_list(h), tags):
            hosts.append(h)
    return hosts


modes.register(
    Mode(
        long_option="list-tag",
        handler_function=mode_list_tag,
        argument=True,
        argument_descr="TAG1 TAG2...",
        argument_optional=True,
        short_help="List hosts having certain tags",
        long_help=["Prints all hosts that have all of the specified tags at once."],
    )
)

# .
#   .--list-checks---------------------------------------------------------.
#   |           _ _     _             _               _                    |
#   |          | (_)___| |_       ___| |__   ___  ___| | _____             |
#   |          | | / __| __|____ / __| '_ \ / _ \/ __| |/ / __|            |
#   |          | | \__ \ ||_____| (__| | | |  __/ (__|   <\__ \            |
#   |          |_|_|___/\__|     \___|_| |_|\___|\___|_|\_\___/            |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class _DSType(enum.Enum):
    ACTIVE = enum.auto()
    SNMP = enum.auto()
    AGENT = enum.auto()
    AGENT_SNMP = enum.auto()


@dataclasses.dataclass(frozen=True)
class _TableRow:
    name: str
    ds_type: _DSType
    title: str

    def render_tty(self) -> str:
        return f"{self._render_name()}{self._render_ds_type()}{self._render_title()}"

    def _render_name(self) -> str:
        return f"{tty.bold}{self.name!s:44}"

    def _render_ds_type(self) -> str:
        match self.ds_type:
            case _DSType.ACTIVE:
                return f"{tty.blue}{'active':10}"
            case _DSType.SNMP:
                return f"{tty.magenta}{'snmp':10}"
            case _DSType.AGENT:
                return f"{tty.yellow}{'agent':10}"
            case _DSType.AGENT_SNMP:
                return f"{tty.yellow}agent{tty.white}/{tty.magenta}snmp"

    def _render_title(self) -> str:
        return f"{tty.normal}{self.title}"


def _get_ds_type(
    check: CheckPlugin, sections: Iterable[AgentSectionPlugin | SNMPSectionPlugin]
) -> _DSType:
    raw_section_is_snmp = {
        isinstance(s, SNMPSectionPlugin)
        for s in filter_relevant_raw_sections(
            consumers=(check,),
            sections=sections,
        ).values()
    }
    if all(raw_section_is_snmp):
        return _DSType.SNMP
    if not any(raw_section_is_snmp):
        return _DSType.AGENT
    return _DSType.AGENT_SNMP


def mode_list_checks() -> None:
    from cmk.utils import man_pages

    plugins = load_checks()
    section_plugins: Iterable[AgentSectionPlugin | SNMPSectionPlugin] = [
        *plugins.agent_sections.values(),
        *plugins.snmp_sections.values(),
    ]

    all_check_manuals = {
        n: man_pages.parse_man_page(n, p)
        for n, p in man_pages.make_man_page_path_map(
            discover_families(raise_errors=cmk.ccc.debug.enabled()),
            PluginGroup.CHECKMAN.value,
        ).items()
    }

    def _get_title(plugin_name: str) -> str:
        try:
            return all_check_manuals[plugin_name].title
        except KeyError:
            return "(no man page present)"

    table = [
        *(
            _TableRow(
                name=(name := f"check_{p.name}"),
                ds_type=_DSType.ACTIVE,
                title=_get_title(name),
            )
            for p in load_active_checks(raise_errors=cmk.ccc.debug.enabled()).values()
        ),
        *(
            _TableRow(
                name=str(plugin.name),
                ds_type=_get_ds_type(plugin, section_plugins),
                title=_get_title(str(plugin.name)),
            )
            for plugin in plugins.check_plugins.values()
        ),
    ]

    for e in sorted(table, key=lambda e: e.name):
        print_(f"{e.render_tty()}\n")


modes.register(
    Mode(
        long_option="list-checks",
        short_option="L",
        handler_function=mode_list_checks,
        short_help="List all available Check_MK checks",
    )
)

# .
#   .--dump-agent----------------------------------------------------------.
#   |        _                                                    _        |
#   |     __| |_   _ _ __ ___  _ __         __ _  __ _  ___ _ __ | |_      |
#   |    / _` | | | | '_ ` _ \| '_ \ _____ / _` |/ _` |/ _ \ '_ \| __|     |
#   |   | (_| | |_| | | | | | | |_) |_____| (_| | (_| |  __/ | | | |_      |
#   |    \__,_|\__,_|_| |_| |_| .__/       \__,_|\__, |\___|_| |_|\__|     |
#   |                         |_|                |___/                     |
#   '----------------------------------------------------------------------'


def mode_dump_agent(options: Mapping[str, object], hostname: HostName) -> None:
    file_cache_options = _handle_fetcher_options(options)

    try:
        snmp_backend_override = parse_snmp_backend(options.get("snmp-backend"))
    except ValueError as exc:
        raise MKBailOut("Unknown SNMP backend") from exc

    plugins = load_checks()
    loading_result = load_config(plugins)
    hosts_config = config.make_hosts_config(loading_result.loaded_config)

    if hostname in hosts_config.clusters:
        raise MKBailOut("Can not be used with cluster hosts")

    config_cache = loading_result.config_cache
    service_name_config = config_cache.make_passive_service_name_config()

    ip_lookup_config = config_cache.ip_lookup_config()
    ip_family = ip_lookup_config.default_address_family(hostname)
    ip_address_of_bare = ip_lookup.make_lookup_ip_address(ip_lookup_config)
    ip_address_of = ip_lookup.ConfiguredIPLookup(
        ip_address_of_bare,
        allow_empty=(),
        error_handler=config.handle_ip_lookup_failure,
    )
    ip_address_of_mgmt = ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config)
    try:
        config_cache.ruleset_matcher.ruleset_optimizer.set_all_processed_hosts({hostname})

        ip_stack_config = ip_lookup_config.ip_stack_config(hostname)
        ipaddress = (
            None
            if ip_stack_config is ip_lookup.IPStackConfig.NO_IP
            else ip_address_of(hostname, ip_family)
        )
        check_interval = config_cache.check_mk_check_interval(hostname)
        stored_walk_path = cmk.utils.paths.snmpwalks_dir
        walk_cache_path = cmk.utils.paths.var_dir / "snmp_cache"
        section_cache_path = cmk.utils.paths.var_dir
        file_cache_path = cmk.utils.paths.data_source_cache_dir
        tcp_cache_path = cmk.utils.paths.tcp_cache_dir
        tls_config = TLSConfig(
            cas_dir=Path(cmk.utils.paths.agent_cas_dir),
            ca_store=Path(cmk.utils.paths.agent_cert_store),
            site_crt=Path(cmk.utils.paths.site_cert_file),
        )
        snmp_scan_config = SNMPScanConfig(
            on_error=OnError.RAISE,
            missing_sys_description=config_cache.missing_sys_description(hostname),
            oid_cache_dir=cmk.utils.paths.snmp_scan_cache_dir,
        )

        output = []
        # Show errors of problematic data sources
        has_errors = False
        pending_passwords_file = cmk.utils.password_store.pending_password_store_path()
        for source in sources.make_sources(
            plugins,
            hostname,
            ip_family,
            ipaddress,
            ip_stack_config,
            fetcher_factory=config_cache.fetcher_factory(
                config_cache.make_service_configurer(plugins.check_plugins, service_name_config),
                ip_address_of,
            ),
            snmp_fetcher_config=SNMPFetcherConfig(
                scan_config=snmp_scan_config,
                selected_sections=NO_SELECTION,
                backend_override=snmp_backend_override,
                stored_walk_path=stored_walk_path,
                walk_cache_path=walk_cache_path,
            ),
            is_cluster=False,
            simulation_mode=config.simulation_mode,
            file_cache_options=file_cache_options,
            file_cache_max_age=MaxAge(
                checking=config.check_max_cachefile_age,
                discovery=1.5 * check_interval,
                inventory=1.5 * check_interval,
            ),
            snmp_backend=config_cache.get_snmp_backend(hostname),
            file_cache_path=file_cache_path,
            tcp_cache_path=tcp_cache_path,
            tls_config=tls_config,
            computed_datasources=config_cache.computed_datasources(hostname),
            datasource_programs=config_cache.datasource_programs(hostname),
            tag_list=config_cache.host_tags.tag_list(hostname),
            management_ip=ip_address_of_mgmt(hostname, ip_family),
            management_protocol=config_cache.management_protocol(hostname),
            special_agent_command_lines=config_cache.special_agent_command_lines(
                hostname,
                ip_family,
                ipaddress,
                passwords=cmk.utils.password_store.load(pending_passwords_file),
                password_store_file=pending_passwords_file,
                ip_address_of=ConfiguredIPLookup(
                    ip_address_of_bare,
                    allow_empty=hosts_config.clusters,
                    error_handler=handle_ip_lookup_failure,
                ),
            ),
            agent_connection_mode=config_cache.agent_connection_mode(hostname),
            check_mk_check_interval=config_cache.check_mk_check_interval(hostname),
        ):
            source_info = source.source_info()
            if source_info.fetcher_type is FetcherType.SNMP:
                continue

            raw_data = get_raw_data(
                source.file_cache(
                    simulation=config.simulation_mode,
                    file_cache_options=file_cache_options,
                ),
                source.fetcher(),
                FetchMode.CHECKING,
            )
            host_sections = parse_raw_data(
                make_parser(
                    config_cache.parser_factory(),
                    source_info.hostname,
                    source_info.fetcher_type,
                    persisted_section_dir=make_persisted_section_dir(
                        source_info.hostname,
                        fetcher_type=source_info.fetcher_type,
                        ident=source_info.ident,
                        section_cache_path=section_cache_path,
                    ),
                    keep_outdated=file_cache_options.keep_outdated,
                    logger=log.logger,
                ),
                raw_data,
                selection=NO_SELECTION,
            )
            source_results = summarize(
                hostname,
                ipaddress,
                host_sections,
                config_cache.summary_config(hostname, source_info.ident),
                fetcher_type=source_info.fetcher_type,
            )
            if any(r.state != 0 for r in source_results):
                summaries = ", ".join(r.summary for r in source_results)
                console.error(f"ERROR [{source_info.ident}]: {summaries}", file=sys.stderr)
                has_errors = True
            if raw_data.is_ok():
                assert raw_data.ok is not None
                output.append(raw_data.ok)

        print_(b"".join(output).decode(errors="surrogateescape"))
        if has_errors:
            sys.exit(1)
    except Exception as e:
        if cmk.ccc.debug.enabled():
            raise
        raise MKBailOut("Unhandled exception: %s" % e)


modes.register(
    Mode(
        long_option="dump-agent",
        short_option="d",
        handler_function=mode_dump_agent,
        argument=True,
        argument_descr="HOSTNAME|ADDRESS",
        short_help="Show raw information from agent",
        long_help=[
            "Shows the raw information received from the given host. For regular "
            "hosts it shows the agent output plus possible piggyback information. "
            "Does not work on clusters but only on real hosts. "
        ],
        sub_options=[*_FETCHER_OPTIONS[:3], _SNMP_BACKEND_OPTION],
    )
)

# .
#   .--dump----------------------------------------------------------------.
#   |                         _                                            |
#   |                      __| |_   _ _ __ ___  _ __                       |
#   |                     / _` | | | | '_ ` _ \| '_ \                      |
#   |                    | (_| | |_| | | | | | | |_) |                     |
#   |                     \__,_|\__,_|_| |_| |_| .__/                      |
#   |                                          |_|                         |
#   '----------------------------------------------------------------------'


def mode_dump_hosts(hostlist: Iterable[HostName]) -> None:
    plugins = load_checks()
    config_cache = load_config(plugins).config_cache
    hosts_config = config_cache.hosts_config
    ip_lookup_config = config_cache.ip_lookup_config()

    ip_address_of = ip_lookup.ConfiguredIPLookup(
        ip_lookup.make_lookup_ip_address(ip_lookup_config),
        allow_empty=config_cache.hosts_config.clusters,
        error_handler=config.handle_ip_lookup_failure,
    )
    ip_address_of_mgmt = ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config)

    all_hosts = {
        hn
        for hn in itertools.chain(hosts_config.hosts, hosts_config.clusters)
        if config_cache.is_active(hn) and config_cache.is_online(hn)
    }
    hosts = set(hostlist)
    if not hosts:
        hosts = all_hosts

    config_cache.ruleset_matcher.ruleset_optimizer.set_all_processed_hosts(hosts)
    service_name_config = config_cache.make_passive_service_name_config()
    for hostname in sorted(hosts - all_hosts):
        sys.stderr.write(f"unknown host: {hostname}\n")
    for hostname in sorted(hosts & all_hosts):
        cmk.base.dump_host.dump_host(
            config_cache,
            service_name_config,
            plugins,
            hostname,
            ip_lookup_config.ip_stack_config(hostname),
            ip_lookup_config.default_address_family(hostname),
            ip_address_of=ip_address_of,
            ip_address_of_mgmt=ip_address_of_mgmt,
            simulation_mode=config.simulation_mode,
        )


modes.register(
    Mode(
        long_option="dump",
        short_option="D",
        handler_function=mode_dump_hosts,
        argument=True,
        argument_descr="H1 H2...",
        argument_optional=True,
        short_help="Dump info about all or some hosts",
        long_help=[
            "Dumps out the complete configuration and information "
            "about one, several or all hosts. It shows all services, hostgroups, "
            "contacts and other information about that host.",
        ],
    )
)


# .
#   .--package-------------------------------------------------------------.
#   |                                 _                                    |
#   |                _ __   __ _  ___| | ____ _  __ _  ___                 |
#   |               | '_ \ / _` |/ __| |/ / _` |/ _` |/ _ \                |
#   |               | |_) | (_| | (__|   < (_| | (_| |  __/                |
#   |               | .__/ \__,_|\___|_|\_\__,_|\__, |\___|                |
#   |               |_|                         |___/                      |
#   '----------------------------------------------------------------------'


_DEPRECATION_MSG = "This command is no longer supported. Please use `mkp%s` instead."


def _fail_with_deprecation_msg(argv: list[str]) -> Literal[1]:
    sys.stdout.write(_DEPRECATION_MSG % " ".join(("", *argv)) + "\n")
    return 1


modes.register(
    Mode(
        long_option="package",
        short_option="P",
        handler_function=_fail_with_deprecation_msg,
        argument=True,
        argument_descr="COMMAND",
        argument_optional=True,
        short_help="DEPRECATED: Do package operations",
        long_help=[_DEPRECATION_MSG % ""],
    )
)

# .
#   .--localize------------------------------------------------------------.
#   |                    _                 _ _                             |
#   |                   | | ___   ___ __ _| (_)_______                     |
#   |                   | |/ _ \ / __/ _` | | |_  / _ \                    |
#   |                   | | (_) | (_| (_| | | |/ /  __/                    |
#   |                   |_|\___/ \___\__,_|_|_/___\___|                    |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def mode_localize(args: list[str]) -> None:
    do_localize(args)


modes.register(
    Mode(
        long_option="localize",
        handler_function=mode_localize,
        argument=True,
        argument_descr="COMMAND",
        argument_optional=True,
        short_help="Do localization operations",
        long_help=[
            "Brings you into localization mode. You can create "
            "and/or improve the localization of Check_MKs GUI. "
            "Call without arguments for a help on localization."
        ],
    )
)

# .
#   .--update-dns-cache----------------------------------------------------.
#   |                        _            _                                |
#   |        _   _ _ __   __| |        __| |_ __  ___        ___           |
#   |       | | | | '_ \ / _` | _____ / _` | '_ \/ __|_____ / __|          |
#   |       | |_| | |_) | (_| ||_____| (_| | | | \__ \_____| (__ _         |
#   |        \__,_| .__/ \__,_(_)     \__,_|_| |_|___/      \___(_)        |
#   |             |_|                                                      |
#   '----------------------------------------------------------------------'


def mode_update_dns_cache() -> None:
    config_cache = config.load(discovery_rulesets=()).config_cache
    hosts_config = config_cache.hosts_config
    ip_lookup.update_dns_cache(
        hosts=(
            hn
            for hn in set(hosts_config.hosts).union(hosts_config.clusters)
            if config_cache.is_active(hn) and config_cache.is_online(hn)
        ),
        ip_lookup_config=config_cache.ip_lookup_config(),
    )


modes.register(
    Mode(
        long_option="update-dns-cache",
        handler_function=mode_update_dns_cache,
        short_help="Update IP address lookup cache",
    )
)

# .
#   .--clean.-piggyb.------------------------------------------------------.
#   |        _                               _                   _         |
#   |    ___| | ___  __ _ _ __         _ __ (_) __ _  __ _ _   _| |__      |
#   |   / __| |/ _ \/ _` | '_ \  _____| '_ \| |/ _` |/ _` | | | | '_ \     |
#   |  | (__| |  __/ (_| | | | ||_____| |_) | | (_| | (_| | |_| | |_) |    |
#   |   \___|_|\___|\__,_|_| |_(_)    | .__/|_|\__, |\__, |\__, |_.__(_)   |
#   |                                 |_|      |___/ |___/ |___/           |
#   '----------------------------------------------------------------------'


def mode_cleanup_piggyback() -> None:
    config_cache = config.load(discovery_rulesets=()).config_cache
    max_age = config_cache.get_definitive_piggybacked_data_expiry_age()
    piggyback_backend.cleanup_piggyback_files(
        cut_off_timestamp=time.time() - max_age, omd_root=cmk.utils.paths.omd_root
    )


modes.register(
    Mode(
        long_option="cleanup-piggyback",
        handler_function=mode_cleanup_piggyback,
        short_help="Cleanup outdated piggyback files",
    )
)

# .
#   .--snmptranslate-------------------------------------------------------.
#   |                            _                       _       _         |
#   |  ___ _ __  _ __ ___  _ __ | |_ _ __ __ _ _ __  ___| | __ _| |_ ___   |
#   | / __| '_ \| '_ ` _ \| '_ \| __| '__/ _` | '_ \/ __| |/ _` | __/ _ \  |
#   | \__ \ | | | | | | | | |_) | |_| | | (_| | | | \__ \ | (_| | ||  __/  |
#   | |___/_| |_|_| |_| |_| .__/ \__|_|  \__,_|_| |_|___/_|\__,_|\__\___|  |
#   |                     |_|                                              |
#   '----------------------------------------------------------------------'


def mode_snmptranslate(walk_filename: str) -> None:
    if not walk_filename:
        raise MKGeneralException("Please provide the name of a SNMP walk file")

    walk_path = cmk.utils.paths.snmpwalks_dir / walk_filename
    if not walk_path.exists():
        raise MKGeneralException("The walk '%s' does not exist" % walk_path)

    command: list[str] = [
        "snmptranslate",
        "-m",
        "ALL",
        "-M+%s" % cmk.utils.paths.local_mib_dir,
        "-",
    ]
    with walk_path.open("rb") as walk_file:
        walk = walk_file.read().split(b"\n")
    while walk[-1] == b"":
        del walk[-1]

    # to be compatible to previous version of this script, we do not feed
    # to original walk to snmptranslate (which would be possible) but a
    # version without values. The output should look like:
    # "[full oid] [value] --> [translated oid]"
    walk_without_values = b"\n".join(line.split(b" ", 1)[0] for line in walk)

    completed_process = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        check=False,
        input=walk_without_values,
    )

    data_translated = completed_process.stdout.split(b"\n")
    # remove last empty line (some tools add a '\n' at the end of the file, others not)
    if data_translated[-1] == b"":
        del data_translated[-1]

    if len(walk) != len(data_translated):
        raise MKGeneralException("call to snmptranslate returned a ambiguous result")

    for element_input, element_translated in zip(walk, data_translated):
        sys.stdout.buffer.write(element_input.strip())
        sys.stdout.buffer.write(b" --> ")
        sys.stdout.buffer.write(element_translated.strip())
        sys.stdout.buffer.write(b"\n")


modes.register(
    Mode(
        long_option="snmptranslate",
        handler_function=mode_snmptranslate,
        argument=True,
        argument_descr="HOST",
        short_help="Do snmptranslate on walk",
        long_help=[
            "Does not contact the host again, but reuses the hosts walk from the "
            "directory %s. You can add further MIBs to the directory %s."
            % (cmk.utils.paths.snmpwalks_dir, cmk.utils.paths.local_mib_dir)
        ],
    )
)

# .
#   .--snmpwalk------------------------------------------------------------.
#   |                                                   _ _                |
#   |            ___ _ __  _ __ ___  _ ____      ____ _| | | __            |
#   |           / __| '_ \| '_ ` _ \| '_ \ \ /\ / / _` | | |/ /            |
#   |           \__ \ | | | | | | | | |_) \ V  V / (_| | |   <             |
#   |           |___/_| |_|_| |_| |_| .__/ \_/\_/ \__,_|_|_|\_\            |
#   |                               |_|                                    |
#   '----------------------------------------------------------------------'

_oids: list[str] = []
_extra_oids: list[str] = []
_SNMPWalkOptions = dict[str, list[OID]]


def _do_snmpwalk(options: _SNMPWalkOptions, *, backend: SNMPBackend) -> None:
    cmk.utils.paths.snmpwalks_dir.mkdir(parents=True, exist_ok=True)

    # TODO: What about SNMP management boards?
    try:
        _do_snmpwalk_on(
            options,
            cmk.utils.paths.snmpwalks_dir / backend.hostname,
            backend=backend,
        )
    except Exception as e:
        console.error(f"Error walking {backend.hostname}: {e}", file=sys.stderr)
        if cmk.ccc.debug.enabled():
            raise
    cmk.ccc.cleanup.cleanup_globals()


def _do_snmpwalk_on(options: _SNMPWalkOptions, filename: Path, *, backend: SNMPBackend) -> None:
    console.verbose(f"{backend.hostname}:")

    oids = oids_to_walk(options)

    with filename.open("w", encoding="utf-8") as file:
        for rows in _execute_walks_for_dump(oids, backend=backend):
            for oid, value in rows:
                file.write(f"{oid} {value}\n")
            console.verbose(f"{len(rows)} variables.")

    console.verbose(f"Wrote fetched data to {tty.bold}{filename}{tty.normal}.")


def _execute_walks_for_dump(
    oids: list[OID], *, backend: SNMPBackend
) -> Iterable[list[tuple[OID, str]]]:
    for oid in oids:
        try:
            console.verbose(f'Walk on "{oid}"...')
            yield walk_for_export(backend.walk(oid, context=""))
        except Exception as e:
            console.error(f"Error: {e}", file=sys.stderr)
            if cmk.ccc.debug.enabled():
                raise


def mode_snmpwalk(options: dict, hostnames: list[str]) -> None:
    if _oids:
        options["oids"] = _oids
    if _extra_oids:
        options["extraoids"] = _extra_oids
    if "oids" in options and "extraoids" in options:
        raise MKGeneralException("You cannot specify --oid and --extraoid at the same time.")

    try:
        snmp_backend_override = parse_snmp_backend(options.get("snmp-backend"))
    except ValueError as exc:
        raise MKBailOut("Unknown SNMP backend") from exc

    if not hostnames:
        raise MKBailOut("Please specify host names to walk on.")

    config_cache = config.load(discovery_rulesets=()).config_cache
    ip_lookup_config = config_cache.ip_lookup_config()
    ip_address_of = ip_lookup.make_lookup_ip_address(ip_lookup_config)

    for hostname in (HostName(hn) for hn in hostnames):
        if ip_lookup_config.ip_stack_config(hostname) is ip_lookup.IPStackConfig.NO_IP:
            raise MKGeneralException(f"Host is configured as No-IP host: {hostname}")

        ip_family = ip_lookup_config.default_address_family(hostname)
        ipaddress = ip_address_of(hostname, ip_family)
        if not ipaddress:
            raise MKGeneralException("Failed to gather IP address of %s" % hostname)

        snmp_config = config_cache.make_snmp_config(
            hostname, ip_family, ipaddress, SourceType.HOST, backend_override=snmp_backend_override
        )
        _do_snmpwalk(
            options,
            backend=snmp_factory.make_backend(
                snmp_config, log.logger, stored_walk_path=cmk.utils.paths.snmpwalks_dir
            ),
        )


modes.register(
    Mode(
        long_option="snmpwalk",
        handler_function=mode_snmpwalk,
        argument=True,
        argument_descr="HOST1 HOST2...",
        argument_optional=True,
        short_help="Do snmpwalk on one or more hosts",
        long_help=[
            "Does a complete snmpwalk for the specified hosts both "
            "on the standard MIB and the enterprises MIB and stores the "
            "result in the directory '%s'. Use the option --oid one or several "
            "times in order to specify alternative OIDs to walk. You need to "
            "specify numeric OIDs. If you want to keep the two standard OIDS "
            ".1.3.6.1.2.1 and .1.3.6.1.4.1 then use --extraoid for just adding "
            "additional OIDs to walk." % cmk.utils.paths.snmpwalks_dir,
        ],
        sub_options=[
            _SNMP_BACKEND_OPTION,
            Option(
                long_option="extraoid",
                argument=True,
                argument_descr="A",
                argument_conv=_extra_oids.append,
                short_help="Walk also on this OID, in addition to mib-2 and "
                "enterprises. You can specify this option multiple "
                "times.",
            ),
            Option(
                long_option="oid",
                argument=True,
                argument_descr="A",
                argument_conv=_oids.append,
                short_help="Walk on this OID instead of mib-2 and enterprises. "
                "You can specify this option multiple times.",
            ),
        ],
    )
)

# .
#   .--snmpget-------------------------------------------------------------.
#   |                                                   _                  |
#   |              ___ _ __  _ __ ___  _ __   __ _  ___| |_                |
#   |             / __| '_ \| '_ ` _ \| '_ \ / _` |/ _ \ __|               |
#   |             \__ \ | | | | | | | | |_) | (_| |  __/ |_                |
#   |             |___/_| |_|_| |_| |_| .__/ \__, |\___|\__|               |
#   |                                 |_|    |___/                         |
#   '----------------------------------------------------------------------'


def mode_snmpget(options: Mapping[str, object], args: Sequence[str]) -> None:
    if not args:
        raise MKBailOut("You need to specify an OID.")
    try:
        snmp_backend_override = parse_snmp_backend(options.get("snmp-backend"))
    except ValueError as exc:
        raise MKBailOut("Unknown SNMP backend") from exc

    config_cache = config.load(discovery_rulesets=()).config_cache
    ip_lookup_config = config_cache.ip_lookup_config()
    ip_address_of = ip_lookup.make_lookup_ip_address(ip_lookup_config)
    oid, *hostnames = args

    if not hostnames:
        hosts_config = config_cache.hosts_config
        hostnames.extend(
            host
            for host in frozenset(hosts_config.hosts)
            if config_cache.is_active(host)
            and config_cache.is_online(host)
            and config_cache.computed_datasources(host).is_snmp
        )

    assert hostnames
    for hostname in (HostName(hn) for hn in hostnames):
        if ip_lookup_config.ip_stack_config(hostname) is ip_lookup.IPStackConfig.NO_IP:
            raise MKGeneralException(f"Host is configured as No-IP host: {hostname}")

        ip_family = ip_lookup_config.default_address_family(hostname)
        ipaddress = ip_address_of(hostname, ip_family)
        if not ipaddress:
            raise MKGeneralException("Failed to gather IP address of %s" % hostname)

        snmp_config = config_cache.make_snmp_config(
            hostname,
            ip_family,
            ipaddress,
            SourceType.HOST,
            backend_override=snmp_backend_override,
        )
        backend = snmp_factory.make_backend(
            snmp_config, log.logger, stored_walk_path=cmk.utils.paths.snmpwalks_dir
        )
        value = get_single_oid(oid, single_oid_cache={}, backend=backend, log=log.logger.debug)
        sys.stdout.write(f"{backend.hostname} ({backend.address}): {value!r}\n")


modes.register(
    Mode(
        long_option="snmpget",
        handler_function=mode_snmpget,
        argument=True,
        argument_descr="OID [HOST1 HOST2...]",
        argument_optional=True,
        short_help="Fetch single OID from one or multiple hosts",
        long_help=[
            "Does a snmpget on the given OID on one or multiple hosts. In case "
            "no host is given, all known SNMP hosts are queried."
        ],
        sub_options=[_SNMP_BACKEND_OPTION],
    )
)

# .
#   .--flush---------------------------------------------------------------.
#   |                         __ _           _                             |
#   |                        / _| |_   _ ___| |__                          |
#   |                       | |_| | | | / __| '_ \                         |
#   |                       |  _| | |_| \__ \ | | |                        |
#   |                       |_| |_|\__,_|___/_| |_|                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def mode_flush(hosts: list[HostName]) -> None:
    plugins = load_checks()
    config_cache = load_config(plugins).config_cache
    hosts_config = config_cache.hosts_config
    service_name_config = config_cache.make_passive_service_name_config()

    effective_host_callback = config.AutochecksConfigurer(
        config_cache, plugins.check_plugins, service_name_config
    ).effective_host

    if not hosts:
        hosts = sorted(
            {
                hn
                for hn in itertools.chain(hosts_config.hosts, hosts_config.clusters)
                if config_cache.is_active(hn) and config_cache.is_online(hn)
            }
        )

    for host in hosts:
        print_("%-20s: " % host)
        flushed = False

        # counters
        try:
            (cmk.utils.paths.counters_dir / host).unlink()
            print_(tty.bold + tty.blue + " counters")
            flushed = True
        except OSError:
            pass

        # cache files
        d = 0
        cache_dir = cmk.utils.paths.tcp_cache_dir
        if os.path.exists(cache_dir):
            for f in os.listdir(cache_dir):
                if f == host or f.startswith(host + "."):
                    try:
                        (cache_dir / f).unlink()
                        d += 1
                        flushed = True
                    except OSError:
                        pass
            if d == 1:
                print_(tty.bold + tty.green + " cache")
            elif d > 1:
                print_(tty.bold + tty.green + " cache(%d)" % d)

        # piggy files from this as source host
        d = piggyback_backend.remove_source_status_file(host, cmk.utils.paths.omd_root)
        if d:
            print_(tty.bold + tty.magenta + " piggyback(1)")

        # logfiles
        log_dir = cmk.utils.paths.logwatch_dir / host
        if log_dir.exists():
            d = 0
            for f in os.listdir(str(log_dir)):
                if f not in [".", ".."]:
                    try:
                        (log_dir / f).unlink()
                        d += 1
                        flushed = True
                    except OSError:
                        pass
            if d > 0:
                print_(tty.bold + tty.magenta + " logfiles(%d)" % d)

        # autochecks
        count = sum(
            remove_autochecks_of_host(node, host, effective_host_callback)
            for node in (config_cache.nodes(host) or [host])
        )
        # config_cache.remove_autochecks(host)
        if count:
            flushed = True
            print_(tty.bold + tty.cyan + " autochecks(%d)" % count)

        # inventory
        path = cmk.utils.paths.var_dir / "inventory" / host
        if path.exists():
            path.unlink()
            print_(tty.bold + tty.yellow + " inventory")

        if not flushed:
            print_("(nothing)")

        print_(tty.normal + "\n")


modes.register(
    Mode(
        long_option="flush",
        handler_function=mode_flush,
        argument=True,
        argument_descr="HOST1 HOST2...",
        argument_optional=True,
        short_help="Flush all data of some or all hosts",
        long_help=[
            "Deletes all runtime data belonging to a host. This includes "
            "the inventorized checks, the state of performance counters, "
            "cached agent output, and logfiles. Precompiled host checks "
            "are not deleted.",
        ],
    )
)

# .
#   .--nagios-config-------------------------------------------------------.
#   |                     _                                  __ _          |
#   |   _ __   __ _  __ _(_) ___  ___        ___ ___  _ __  / _(_) __ _    |
#   |  | '_ \ / _` |/ _` | |/ _ \/ __|_____ / __/ _ \| '_ \| |_| |/ _` |   |
#   |  | | | | (_| | (_| | | (_) \__ \_____| (_| (_) | | | |  _| | (_| |   |
#   |  |_| |_|\__,_|\__, |_|\___/|___/      \___\___/|_| |_|_| |_|\__, |   |
#   |               |___/                                         |___/    |
#   '----------------------------------------------------------------------'


def mode_dump_nagios_config(args: Sequence[HostName]) -> None:
    from cmk.utils.config_path import VersionedConfigPath

    from cmk.base.core_nagios import create_config

    plugins = load_checks()
    loading_result = load_config(plugins)
    config_cache = load_config(plugins).config_cache
    ip_lookup_config = config_cache.ip_lookup_config()

    hostnames = args if args else None

    if config.host_notification_periods:
        config_warnings.warn(
            "host_notification_periods is not longer supported. Please use extra_host_conf['notification_period'] instead."
        )

    if config.service_notification_periods:
        config_warnings.warn(
            "service_notification_periods is not longer supported. Please use extra_service_conf['notification_period'] instead."
        )

    hosts_config = config_cache.hosts_config
    if hostnames is None:
        hostnames = sorted(
            {
                hn
                for hn in itertools.chain(hosts_config.hosts, hosts_config.clusters)
                if config_cache.is_active(hn) and config_cache.is_online(hn)
            }
        )
    else:
        hostnames = sorted(hostnames)

    create_config(
        sys.stdout,
        Path(VersionedConfigPath.next()),
        config_cache,
        config_cache.make_passive_service_name_config(),
        plugins.check_plugins,
        hostnames=hostnames,
        licensing_handler=get_licensing_handler_type().make(),
        passwords=cmk.utils.password_store.load(
            cmk.utils.password_store.pending_password_store_path()
        ),
        get_ip_stack_config=ip_lookup_config.ip_stack_config,
        default_address_family=ip_lookup_config.default_address_family,
        ip_address_of=ip_lookup.ConfiguredIPLookup(
            ip_lookup.make_lookup_ip_address(ip_lookup_config),
            allow_empty=hosts_config.clusters,
            error_handler=config.handle_ip_lookup_failure,
        ),
        service_depends_on=config.ServiceDependsOn(
            tag_list=config_cache.host_tags.tag_list,
            service_dependencies=loading_result.loaded_config.service_dependencies,
        ),
    )


modes.register(
    Mode(
        long_option="nagios-config",
        short_option="N",
        handler_function=mode_dump_nagios_config,
        argument=True,
        argument_descr="HOST1 HOST2...",
        argument_optional=True,
        short_help="Output Nagios configuration",
        long_help=[
            "Outputs the Nagios configuration. You may optionally add a list "
            "of hosts. In that case the configuration is generated only for "
            "that hosts (useful for debugging).",
        ],
    )
)

# .
#   .--update--------------------------------------------------------------.
#   |                                   _       _                          |
#   |                   _   _ _ __   __| | __ _| |_ ___                    |
#   |                  | | | | '_ \ / _` |/ _` | __/ _ \                   |
#   |                  | |_| | |_) | (_| | (_| | ||  __/                   |
#   |                   \__,_| .__/ \__,_|\__,_|\__\___|                   |
#   |                        |_|                                           |
#   '----------------------------------------------------------------------'


def _make_configured_bake_on_restart(
    loading_result: config.LoadingResult,
    hosts: Sequence[HostAddress],
) -> Callable[[], None]:
    # TODO: consider passing the edition here, instead of "detecting" it (and thus
    # silently failing if the bakery is missing unexpectedly)
    try:
        from cmk.base.configlib.cee.bakery import (  # type: ignore[import-untyped, unused-ignore, import-not-found]
            make_configured_bake_on_restart_callback,
        )
    except ImportError:
        return lambda: None

    return make_configured_bake_on_restart_callback(
        loading_result,
        hosts,
        agents_dir=cmk.utils.paths.agents_dir,
        local_agents_dir=cmk.utils.paths.local_agents_dir,
    )


def mode_update() -> None:
    from cmk.base.core_config import do_create_config

    plugins = load_checks()
    loading_result = load_config(plugins)

    hosts_config = loading_result.config_cache.hosts_config
    ip_lookup_config = loading_result.config_cache.ip_lookup_config()
    ip_address_of = ip_lookup.ConfiguredIPLookup(
        ip_lookup.make_lookup_ip_address(ip_lookup_config),
        allow_empty=hosts_config.clusters,
        error_handler=ip_lookup.CollectFailedHosts(),
    )

    bake_on_restart = _make_configured_bake_on_restart(loading_result, hosts_config.hosts)

    try:
        with cmk.base.core.activation_lock(mode=config.restart_locking):
            do_create_config(
                core=create_core(config.monitoring_core),
                hosts_config=hosts_config,
                config_cache=loading_result.config_cache,
                service_name_config=loading_result.config_cache.make_passive_service_name_config(),
                plugins=plugins,
                discovery_rules=loading_result.loaded_config.discovery_rules,
                get_ip_stack_config=ip_lookup_config.ip_stack_config,
                default_address_family=ip_lookup_config.default_address_family,
                ip_address_of=ip_address_of,
                ip_address_of_mgmt=ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config),
                hosts_to_update=None,
                service_depends_on=config.ServiceDependsOn(
                    tag_list=loading_result.config_cache.host_tags.tag_list,
                    service_dependencies=loading_result.loaded_config.service_dependencies,
                ),
                duplicates=sorted(
                    hosts_config.duplicates(
                        lambda hn: loading_result.config_cache.is_active(hn)
                        and loading_result.config_cache.is_online(hn)
                    )
                ),
                bake_on_restart=bake_on_restart,
            )
    except Exception as e:
        console.error(f"Configuration Error: {e}", file=sys.stderr)
        if cmk.ccc.debug.enabled():
            raise
        sys.exit(1)

    for warning in ip_address_of.error_handler.format_errors():
        console.warning(tty.format_warning(f"\n{warning}"))


modes.register(
    Mode(
        long_option="update",
        short_option="U",
        handler_function=mode_update,
        short_help="Create core config",
        long_help=[
            "Updates the core configuration based on the current Checkmk "
            "configuration. When using the Nagios core, the precompiled host "
            "checks are created and the nagios configuration is updated. "
            "When using the CheckMK Micro Core, the core configuration is created "
            "and the configuration for the Core helper processes is being created.",
            "The Agent Bakery is updating the agents.",
        ],
    )
)

# .
#   .--restart-------------------------------------------------------------.
#   |                                 _             _                      |
#   |                   _ __ ___  ___| |_ __ _ _ __| |_                    |
#   |                  | '__/ _ \/ __| __/ _` | '__| __|                   |
#   |                  | | |  __/\__ \ || (_| | |  | |_                    |
#   |                  |_|  \___||___/\__\__,_|_|   \__|                   |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def mode_restart(args: Sequence[HostName]) -> None:
    plugins = load_checks()
    loading_result = load_config(plugins)
    hosts_config = loading_result.config_cache.hosts_config
    ip_lookup_config = loading_result.config_cache.ip_lookup_config()

    ip_address_of = ip_lookup.ConfiguredIPLookup(
        ip_lookup.make_lookup_ip_address(ip_lookup_config),
        allow_empty=hosts_config.clusters,
        error_handler=ip_lookup.CollectFailedHosts(),
    )
    ip_address_of_mgmt = ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config)

    cmk.base.core.do_restart(
        loading_result.config_cache,
        hosts_config,
        loading_result.config_cache.make_passive_service_name_config(),
        ip_lookup_config.ip_stack_config,
        ip_lookup_config.default_address_family,
        ip_address_of,
        ip_address_of_mgmt,
        create_core(config.monitoring_core),
        plugins,
        hosts_to_update=set(args) if args else None,
        locking_mode=config.restart_locking,
        service_depends_on=config.ServiceDependsOn(
            tag_list=loading_result.config_cache.host_tags.tag_list,
            service_dependencies=loading_result.loaded_config.service_dependencies,
        ),
        discovery_rules=loading_result.loaded_config.discovery_rules,
        duplicates=sorted(
            hosts_config.duplicates(
                lambda hn: loading_result.config_cache.is_active(hn)
                and loading_result.config_cache.is_online(hn)
            )
        ),
        bake_on_restart=_make_configured_bake_on_restart(loading_result, hosts_config.hosts),
    )
    for warning in ip_address_of.error_handler.format_errors():
        console.warning(tty.format_warning(f"\n{warning}"))


modes.register(
    Mode(
        long_option="restart",
        short_option="R",
        argument=True,
        argument_optional=True,
        argument_descr="[HostA, HostB]",
        long_help=[
            "You may add host names as additional arguments. This enables the incremental "
            "activate mechanism, only compiling these host names and using cached data for all "
            "other hosts. Only supported with Checkmk Micro Core."
        ],
        handler_function=mode_restart,
        short_help="Create core config + core restart",
    )
)

# .
#   .--reload--------------------------------------------------------------.
#   |                             _                 _                      |
#   |                    _ __ ___| | ___   __ _  __| |                     |
#   |                   | '__/ _ \ |/ _ \ / _` |/ _` |                     |
#   |                   | | |  __/ | (_) | (_| | (_| |                     |
#   |                   |_|  \___|_|\___/ \__,_|\__,_|                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def mode_reload(args: Sequence[HostName]) -> None:
    plugins = load_checks()
    loading_result = load_config(plugins)
    hosts_config = loading_result.config_cache.hosts_config
    ip_lookup_config = loading_result.config_cache.ip_lookup_config()

    ip_address_of = ip_lookup.ConfiguredIPLookup(
        ip_lookup.make_lookup_ip_address(ip_lookup_config),
        allow_empty=hosts_config.clusters,
        error_handler=ip_lookup.CollectFailedHosts(),
    )
    ip_address_of_mgmt = ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config)

    cmk.base.core.do_reload(
        loading_result.config_cache,
        hosts_config,
        loading_result.config_cache.make_passive_service_name_config(),
        ip_lookup_config.ip_stack_config,
        ip_lookup_config.default_address_family,
        ip_address_of,
        ip_address_of_mgmt,
        create_core(config.monitoring_core),
        plugins,
        hosts_to_update=set(args) if args else None,
        locking_mode=config.restart_locking,
        service_depends_on=config.ServiceDependsOn(
            tag_list=loading_result.config_cache.host_tags.tag_list,
            service_dependencies=loading_result.loaded_config.service_dependencies,
        ),
        discovery_rules=loading_result.loaded_config.discovery_rules,
        duplicates=sorted(
            hosts_config.duplicates(
                lambda hn: loading_result.config_cache.is_active(hn)
                and loading_result.config_cache.is_online(hn)
            ),
        ),
        bake_on_restart=_make_configured_bake_on_restart(loading_result, hosts_config.hosts),
    )
    for warning in ip_address_of.error_handler.format_errors():
        console.warning(tty.format_warning(f"\n{warning}"))


modes.register(
    Mode(
        long_option="reload",
        short_option="O",
        argument=True,
        argument_optional=True,
        argument_descr="[HostA, HostB]",
        long_help=[
            "You may add host names as additional arguments. This enables the incremental "
            "activate mechanism, only compiling these host names and using cached data for all "
            "other hosts. Only supported with Checkmk Micro Core."
        ],
        handler_function=mode_reload,
        short_help="Create core config + core reload",
    )
)

# .
#   .--man-----------------------------------------------------------------.
#   |                                                                      |
#   |                        _ __ ___   __ _ _ __                          |
#   |                       | '_ ` _ \ / _` | '_ \                         |
#   |                       | | | | | | (_| | | | |                        |
#   |                       |_| |_| |_|\__,_|_| |_|                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def mode_man(options: Mapping[str, str], args: list[str]) -> None:
    from cmk.utils import man_pages

    man_page_path_map = man_pages.make_man_page_path_map(
        discover_families(raise_errors=cmk.ccc.debug.enabled()),
        PluginGroup.CHECKMAN.value,
    )
    if not args:
        man_pages.print_man_page_table(man_page_path_map)
        return

    if (man_page_path := man_page_path_map.get(args[0])) is None:
        raise MKBailOut(f"No manpage for {args[0]}. Sorry.")

    man_page = man_pages.parse_man_page(args[0], man_page_path)
    renderer: type[man_pages.ConsoleManPageRenderer] | type[man_pages.NowikiManPageRenderer]
    match options.get("renderer", "console"):
        case "console":
            renderer = man_pages.ConsoleManPageRenderer
        case "nowiki":
            renderer = man_pages.NowikiManPageRenderer
        case other:
            raise ValueError(other)

    try:
        rendered = renderer(man_page).render_page()
    except Exception as exc:
        sys.stdout.write(f"ERROR: Invalid check manpage {args[0]}: {exc}\n")

    man_pages.write_output(rendered)


modes.register(
    Mode(
        long_option="man",
        short_option="M",
        handler_function=mode_man,
        argument=True,
        argument_descr="CHECKTYPE",
        argument_optional=True,
        short_help="Show manpage for check CHECKTYPE",
        long_help=[
            "Shows documentation about a check type. If /usr/bin/less is "
            "available it is used as pager. Exit by pressing Q. "
            "Use -M without an argument to show a list of all manual pages."
        ],
        sub_options=[
            Option(
                long_option="renderer",
                short_option="r",
                argument=True,
                argument_descr="RENDERER",
                short_help="Use the given renderer: 'console' or 'nowiki'. Defaults to 'console'.",
            ),
        ],
    )
)

# .
#   .--browse-man----------------------------------------------------------.
#   |    _                                                                 |
#   |   | |__  _ __ _____      _____  ___       _ __ ___   __ _ _ __       |
#   |   | '_ \| '__/ _ \ \ /\ / / __|/ _ \_____| '_ ` _ \ / _` | '_ \      |
#   |   | |_) | | | (_) \ V  V /\__ \  __/_____| | | | | | (_| | | | |     |
#   |   |_.__/|_|  \___/ \_/\_/ |___/\___|     |_| |_| |_|\__,_|_| |_|     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def mode_browse_man() -> None:
    from cmk.utils import man_pages

    man_pages.print_man_page_browser(
        man_pages.load_man_page_catalog(
            discover_families(raise_errors=cmk.ccc.debug.enabled()),
            PluginGroup.CHECKMAN.value,
        )
    )


modes.register(
    Mode(
        long_option="browse-man",
        short_option="m",
        handler_function=mode_browse_man,
        short_help="Open interactive manpage browser",
    )
)

# .
#   .--automation----------------------------------------------------------.
#   |                   _                        _   _                     |
#   |        __ _ _   _| |_ ___  _ __ ___   __ _| |_(_) ___  _ __          |
#   |       / _` | | | | __/ _ \| '_ ` _ \ / _` | __| |/ _ \| '_ \         |
#   |      | (_| | |_| | || (_) | | | | | | (_| | |_| | (_) | | | |        |
#   |       \__,_|\__,_|\__\___/|_| |_| |_|\__,_|\__|_|\___/|_| |_|        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def mode_automation(args: list[str]) -> None:
    from cmk.base import automations

    if not args:
        raise automations.MKAutomationError("You need to provide arguments")

    # At least for the automation calls that buffer and handle the stdout/stderr on their own
    # we can now enable this. In the future we should remove this call for all automations calls and
    # handle the output in a common way.
    if args[0] not in [
        "restart",
        "reload",
        "start",
        "create-diagnostics-dump",
        "service-discovery-preview",
    ]:
        log.logger.handlers[:] = []
        log.logger.addHandler(logging.NullHandler())
        log.logger.setLevel(logging.INFO)

    name, automation_args = args[0], args[1:]
    with tracer.span(
        f"mode_automation[{name}]",
        attributes={
            "cmk.automation.name": name,
            "cmk.automation.args": automation_args,
        },
    ):
        sys.exit(
            automations.automations.execute_and_write_serialized_result_to_stdout(
                name, automation_args
            )
        )


modes.register(
    Mode(
        long_option="automation",
        handler_function=mode_automation,
        argument=True,
        argument_descr="COMMAND...",
        argument_optional=True,
        short_help="Internal helper to invoke Check_MK actions",
    )
)

# .
#   .--notify--------------------------------------------------------------.
#   |                                 _   _  __                            |
#   |                     _ __   ___ | |_(_)/ _|_   _                      |
#   |                    | '_ \ / _ \| __| | |_| | | |                     |
#   |                    | | | | (_) | |_| |  _| |_| |                     |
#   |                    |_| |_|\___/ \__|_|_|  \__, |                     |
#   |                                           |___/                      |
#   '----------------------------------------------------------------------'


def mode_notify(options: dict, args: list[str]) -> int | None:
    from cmk.base import notify

    with store.lock_checkmk_configuration(configuration_lockfile):
        loaded_config = config.load(discovery_rulesets=(), with_conf_d=True, validate_hosts=False)

    def ensure_nagios(msg: str) -> None:
        if config.is_cmc():
            raise RuntimeError(msg)

    keepalive = "keepalive" in options and (
        cmk_version.edition(cmk.utils.paths.omd_root) is not cmk_version.Edition.CRE
    )
    if keepalive:
        register_sigint_handler()

    return notify.do_notify(
        options,
        args,
        define_servicegroups=config.define_servicegroups,
        host_parameters_cb=lambda hostname,
        plugin: loaded_config.config_cache.notification_plugin_parameters(hostname, plugin),
        rules=config.notification_rules,
        parameters=config.notification_parameter,
        get_http_proxy=config.get_http_proxy,
        ensure_nagios=ensure_nagios,
        bulk_interval=config.notification_bulk_interval,
        plugin_timeout=config.notification_plugin_timeout,
        config_contacts=config.contacts,
        fallback_email=config.notification_fallback_email,
        fallback_format=config.notification_fallback_format,
        spooling=ConfigCache.notification_spooling(),
        backlog_size=config.notification_backlog,
        logging_level=ConfigCache.notification_logging_level(),
        keepalive=keepalive,
        all_timeperiods=load_timeperiods(),
    )


modes.register(
    Mode(
        long_option="notify",
        handler_function=mode_notify,
        argument=True,
        argument_descr="MODE",
        argument_optional=True,
        short_help="Used to send notifications from core",
        # TODO: Write long help
        sub_options=[
            Option(
                long_option="log-to-stdout",
                short_help="Also write log messages to console",
            ),
            Option(
                long_option="keepalive",
                short_help="Execute in keepalive mode (CEE only)",
            ),
        ],
    )
)


# .
#   .--check-discovery-----------------------------------------------------.
#   |       _     _               _ _                                      |
#   |   ___| |__ | | __        __| (_)___  ___ _____   _____ _ __ _   _    |
#   |  / __| '_ \| |/ / _____ / _` | / __|/ __/ _ \ \ / / _ \ '__| | | |   |
#   | | (__| | | |   < |_____| (_| | \__ \ (_| (_) \ V /  __/ |  | |_| |   |
#   |  \___|_| |_|_|\_(_)     \__,_|_|___/\___\___/ \_/ \___|_|   \__, |   |
#   |                                                             |___/    |
#   '----------------------------------------------------------------------'


def mode_check_discovery(options: Mapping[str, object], hostname: HostName) -> int:
    file_cache_options = _handle_fetcher_options(options)
    try:
        snmp_backend_override = parse_snmp_backend(options.get("snmp-backend"))
    except ValueError as exc:
        raise MKBailOut("Unknown SNMP backend") from exc

    plugins = load_checks()
    loading_result = load_config(plugins)
    config_cache = loading_result.config_cache

    ruleset_matcher = config_cache.ruleset_matcher
    ruleset_matcher.ruleset_optimizer.set_all_processed_hosts({hostname})
    service_name_config = config_cache.make_passive_service_name_config()
    autochecks_config = config.AutochecksConfigurer(
        config_cache, plugins.check_plugins, service_name_config
    )
    discovery_config = DiscoveryConfig(
        ruleset_matcher,
        loading_result.config_cache.label_manager.labels_of_host,
        loading_result.loaded_config.discovery_rules,
    )
    ip_lookup_config = config_cache.ip_lookup_config()
    ip_address_of = ip_lookup.ConfiguredIPLookup(
        ip_lookup.make_lookup_ip_address(ip_lookup_config),
        allow_empty=config_cache.hosts_config.clusters,
        error_handler=config.handle_ip_lookup_failure,
    )
    check_interval = config_cache.check_mk_check_interval(hostname)
    discovery_file_cache_max_age = 1.5 * check_interval if file_cache_options.use_outdated else 0
    fetcher = CMKFetcher(
        config_cache,
        config_cache.fetcher_factory(
            config_cache.make_service_configurer(plugins.check_plugins, service_name_config),
            ip_address_of,
        ),
        plugins,
        default_address_family=ip_lookup_config.default_address_family,
        file_cache_options=file_cache_options,
        force_snmp_cache_refresh=False,
        get_ip_stack_config=ip_lookup_config.ip_stack_config,
        ip_address_of=ip_address_of,
        ip_address_of_mandatory=ip_lookup.make_lookup_ip_address(ip_lookup_config),
        ip_address_of_mgmt=ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config),
        mode=FetchMode.DISCOVERY,
        on_error=OnError.RAISE,
        selected_sections=NO_SELECTION,
        simulation_mode=config.simulation_mode,
        max_cachefile_age=MaxAge(
            checking=config.check_max_cachefile_age,
            discovery=discovery_file_cache_max_age,
            inventory=1.5 * check_interval,
        ),
        snmp_backend_override=snmp_backend_override,
        password_store_file=cmk.utils.password_store.core_password_store_path(),
    )
    parser = CMKParser(
        config_cache.parser_factory(),
        selected_sections=NO_SELECTION,
        keep_outdated=file_cache_options.keep_outdated,
        logger=logging.getLogger("cmk.base.discovery"),
    )
    summarizer = CMKSummarizer(
        hostname,
        config_cache.summary_config,
        override_non_ok_state=None,
    )
    error_handler = CheckResultErrorHandler(
        exit_spec=config_cache.exit_code_spec(hostname),
        host_name=hostname,
        service_name="Check_MK Discovery",
        plugin_name="discover",
        is_cluster=hostname in config_cache.hosts_config.clusters,
        snmp_backend=config_cache.get_snmp_backend(hostname),
        keepalive=False,
    )

    check_results: Sequence[ActiveCheckResult] = []
    with error_handler:
        fetched = fetcher(hostname, ip_address=None)
        with CPUTracker(console.debug) as tracker:
            check_results = execute_check_discovery(
                hostname,
                is_cluster=hostname in config_cache.hosts_config.clusters,
                cluster_nodes=config_cache.nodes(hostname),
                params=config_cache.discovery_check_parameters(hostname),
                fetched=((f[0], f[1]) for f in fetched),
                parser=parser,
                summarizer=summarizer,
                section_plugins=SectionPluginMapper(
                    {**plugins.agent_sections, **plugins.snmp_sections}
                ),
                section_error_handling=lambda section_name, raw_data: create_section_crash_dump(
                    operation="parsing",
                    section_name=section_name,
                    section_content=raw_data,
                    host_name=hostname,
                    rtc_package=None,
                ),
                host_label_plugins=HostLabelPluginMapper(
                    discovery_config=discovery_config,
                    sections={**plugins.agent_sections, **plugins.snmp_sections},
                ),
                plugins=DiscoveryPluginMapper(
                    discovery_config=discovery_config,
                    check_plugins=plugins.check_plugins,
                ),
                autochecks_config=autochecks_config,
                enforced_services=config_cache.enforced_services_table(
                    hostname, plugins.check_plugins, service_name_config
                ),
            )
        check_results = [
            *check_results,
            make_timing_results(
                tracker.duration,
                tuple((f[0], f[2]) for f in fetched),
                perfdata_with_times=config.check_mk_perfdata_with_times,
            ),
        ]

    if error_handler.result is not None:
        check_results = (error_handler.result,)

    check_result = ActiveCheckResult.from_subresults(*check_results)
    with suppress(IOError):
        sys.stdout.write(check_result.as_text() + "\n")
        sys.stdout.flush()
    return check_result.state


modes.register(
    Mode(
        long_option="check-discovery",
        handler_function=mode_check_discovery,
        argument=True,
        argument_descr="HOSTNAME",
        short_help="Check for not yet monitored services",
        long_help=[
            "Make Check_MK behave as monitoring plug-ins that checks if an "
            "inventory would find new or vanished services for the host. "
            "If configured to do so, this will queue those hosts for automatic "
            "autodiscovery"
        ],
        sub_options=[*_FETCHER_OPTIONS, _SNMP_BACKEND_OPTION],
    )
)


# .
#   .--discover------------------------------------------------------------.
#   |                     _ _                                              |
#   |                  __| (_)___  ___ _____   _____ _ __                  |
#   |                 / _` | / __|/ __/ _ \ \ / / _ \ '__|                 |
#   |                | (_| | \__ \ (_| (_) \ V /  __/ |                    |
#   |                 \__,_|_|___/\___\___/ \_/ \___|_|                    |
#   |                                                                      |
#   '----------------------------------------------------------------------'

_TName = TypeVar("_TName", str, CheckPluginName, InventoryPluginName, SectionName)


def _convert_sections_argument(arg: str) -> set[SectionName]:
    try:
        # kindly forgive empty strings
        return {SectionName(n) for n in arg.split(",") if n}
    except ValueError as exc:
        raise MKBailOut("Error in --detect-sections argument: %s" % exc)


_option_sections = Option(
    long_option="detect-sections",
    short_help=(
        "Comma separated list of sections. The provided sections (but no more) will be"
        " available (skipping SNMP detection)"
    ),
    argument=True,
    argument_descr="S",
    argument_conv=_convert_sections_argument,
)


def _get_plugins_option(type_: type[_TName]) -> Option:
    def _convert_plugins_argument(arg: str) -> set[_TName]:
        try:
            # kindly forgive empty strings
            return {type_(n) for n in arg.split(",") if n}
        except ValueError as exc:
            raise MKBailOut("Error in --plugins argument: %s" % exc) from exc

    return Option(
        long_option="plugins",
        short_help="Restrict discovery, checking or inventory to these plugins",
        argument=True,
        argument_descr="P",
        argument_conv=_convert_plugins_argument,
    )


def _convert_detect_plugins_argument(arg: str) -> set[str]:
    try:
        # kindly forgive empty strings
        # also maincheckify, as we may be dealing with old "--checks" input including dots.
        return {maincheckify(n) for n in arg.split(",") if n}
    except ValueError as exc:
        raise MKBailOut("Error in --detect-plugins argument: %s" % exc) from exc


_option_detect_plugins = Option(
    long_option="detect-plugins",
    deprecated_long_options={"checks"},
    short_help="Same as '--plugins', but implies a best efford guess for --detect-sections",
    argument=True,
    argument_descr="P",
    argument_conv=_convert_detect_plugins_argument,
)

_PluginName = TypeVar("_PluginName", CheckPluginName, InventoryPluginName)


def _lookup_plugin(
    plugin_name: _PluginName, plugins: Mapping[_PluginName, CheckPlugin | InventoryPlugin]
) -> CheckPlugin | InventoryPlugin:
    try:
        return plugins[plugin_name]
    except KeyError as exc:
        raise MKBailOut(f"Unknown check plugin '{plugin_name}'") from exc


def _extract_plugin_selection(
    options: "_CheckingOptions | _DiscoveryOptions | _InventoryOptions",
    plugins: Mapping[_PluginName, CheckPlugin | InventoryPlugin],
    sections: Iterable[AgentSectionPlugin | SNMPSectionPlugin],
    type_: type[_PluginName],
) -> tuple[SectionNameCollection, Container]:
    detect_plugins = options.get("detect-plugins")
    if detect_plugins is None:
        return (
            options.get("detect-sections", NO_SELECTION),
            options.get("plugins", EVERYTHING),
        )

    conflicting_options = {"detect-sections", "plugins"}
    if conflicting_options.intersection(options):
        raise MKBailOut(
            "Option '--detect-plugins' must not be combined with %s"
            % "/".join(f"--{o}" for o in conflicting_options)
        )

    if detect_plugins == {"@all"}:
        # this is the same as ommitting the option entirely.
        # (mo) ... which is weird, because specifiying *all* plugins would do
        # something different. Keeping this for compatibility with old --checks
        return NO_SELECTION, EVERYTHING

    plugin_names = {type_(p) for p in detect_plugins}
    return (
        frozenset(
            filter_relevant_raw_sections(
                consumers=(_lookup_plugin(pn, plugins) for pn in plugin_names),
                sections=sections,
            )
        ),
        plugin_names,
    )


_DiscoveryOptions = TypedDict(
    "_DiscoveryOptions",
    {
        "cache": Literal[True],
        "no-cache": Literal[True],
        "no-tcp": Literal[True],
        "usewalk": Literal[True],
        "detect-sections": frozenset[SectionName],
        "plugins": frozenset[CheckPluginName],
        "detect-plugins": frozenset[str],
        "discover": int,
        "only-host-labels": bool,
    },
    total=False,
)


def _preprocess_hostnames(
    arg_host_names: frozenset[HostName],
    is_cluster: Callable[[HostName], bool],
    resolve_nodes: Callable[[HostName], Iterable[HostName]],
    config_cache: ConfigCache,
    only_host_labels: bool,
) -> set[HostName]:
    """Default to all hosts and expand cluster names to their nodes"""
    svc = "" if only_host_labels else "services and "
    if not arg_host_names:
        console.verbose(f"Discovering {svc}host labels on all hosts")
        hosts_config = config_cache.hosts_config
        return {
            hn
            for hn in hosts_config.hosts
            if config_cache.is_active(hn) and config_cache.is_online(hn)
        }
    node_names = {
        node_name
        for host_name in arg_host_names
        for node_name in (resolve_nodes(host_name) if is_cluster(host_name) else (host_name,))
    }
    console.verbose(f"Discovering {svc}host labels on: {', '.join(sorted(node_names))}")
    return node_names


def mode_discover(options: _DiscoveryOptions, args: list[str]) -> None:
    plugins = load_checks()
    loading_result = load_config(plugins)
    config_cache = loading_result.config_cache
    discovery_config = DiscoveryConfig(
        loading_result.config_cache.ruleset_matcher,
        loading_result.config_cache.label_manager.labels_of_host,
        loading_result.loaded_config.discovery_rules,
    )
    hosts_config = config.make_hosts_config(loading_result.loaded_config)
    service_name_config = config_cache.make_passive_service_name_config()
    ip_lookup_config = config_cache.ip_lookup_config()
    ip_address_of = ip_lookup.ConfiguredIPLookup(
        ip_lookup.make_lookup_ip_address(ip_lookup_config),
        allow_empty=config_cache.hosts_config.clusters,
        error_handler=config.handle_ip_lookup_failure,
    )

    hostnames = modes.parse_hostname_list(config_cache, hosts_config, args)
    if hostnames:
        # In case of discovery with host restriction, do not use the cache
        # file by default as -I and -II are used for debugging.
        file_cache_options = FileCacheOptions(disabled=True, use_outdated=False)
        config_cache.ruleset_matcher.ruleset_optimizer.set_all_processed_hosts(set(hostnames))
    else:
        # In case of discovery without host restriction, use the cache file
        # by default. Otherwise Checkmk would have to connect to ALL hosts.
        file_cache_options = FileCacheOptions(disabled=False, use_outdated=True)

    file_cache_options = _handle_fetcher_options(options, defaults=file_cache_options)
    try:
        snmp_backend_override = parse_snmp_backend(options.get("snmp-backend"))
    except ValueError as exc:
        raise MKBailOut("Unknown SNMP backend") from exc

    on_error = OnError.RAISE if cmk.ccc.debug.enabled() else OnError.WARN
    selected_sections, run_plugin_names = _extract_plugin_selection(
        options,
        plugins.check_plugins,
        itertools.chain(plugins.agent_sections.values(), plugins.snmp_sections.values()),
        CheckPluginName,
    )
    parser = CMKParser(
        config_cache.parser_factory(),
        selected_sections=selected_sections,
        keep_outdated=file_cache_options.keep_outdated,
        logger=logging.getLogger("cmk.base.discovery"),
    )
    fetcher = CMKFetcher(
        config_cache,
        config_cache.fetcher_factory(
            config_cache.make_service_configurer(plugins.check_plugins, service_name_config),
            ip_address_of,
        ),
        plugins,
        default_address_family=ip_lookup_config.default_address_family,
        file_cache_options=file_cache_options,
        force_snmp_cache_refresh=False,
        get_ip_stack_config=ip_lookup_config.ip_stack_config,
        ip_address_of=ip_address_of,
        ip_address_of_mandatory=ip_lookup.make_lookup_ip_address(ip_lookup_config),
        ip_address_of_mgmt=ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config),
        mode=(
            FetchMode.DISCOVERY if selected_sections is NO_SELECTION else FetchMode.FORCE_SECTIONS
        ),
        on_error=on_error,
        selected_sections=selected_sections,
        simulation_mode=config.simulation_mode,
        snmp_backend_override=snmp_backend_override,
        password_store_file=cmk.utils.password_store.pending_password_store_path(),
    )
    for hostname in sorted(
        _preprocess_hostnames(
            frozenset(hostnames),
            is_cluster=lambda hn: hn in config_cache.hosts_config.clusters,
            resolve_nodes=config_cache.nodes,
            config_cache=config_cache,
            only_host_labels="only-host-labels" in options,
        )
    ):

        def section_error_handling(
            section_name: SectionName,
            raw_data: Sequence[object],
            host_name: HostName = hostname,
        ) -> str:
            return create_section_crash_dump(
                operation="parsing",
                section_name=section_name,
                section_content=raw_data,
                host_name=host_name,
                rtc_package=None,
            )

        commandline_discovery(
            hostname,
            clear_ruleset_matcher_caches=(config_cache.ruleset_matcher.clear_caches),
            parser=parser,
            fetcher=fetcher,
            section_plugins=SectionPluginMapper(
                {**plugins.agent_sections, **plugins.snmp_sections}
            ),
            section_error_handling=section_error_handling,
            host_label_plugins=HostLabelPluginMapper(
                discovery_config=discovery_config,
                sections={**plugins.agent_sections, **plugins.snmp_sections},
            ),
            plugins=DiscoveryPluginMapper(
                discovery_config=discovery_config,
                check_plugins=plugins.check_plugins,
            ),
            run_plugin_names=run_plugin_names,
            ignore_plugin=config_cache.check_plugin_ignored,
            arg_only_new=options["discover"] == 1,
            only_host_labels="only-host-labels" in options,
            on_error=on_error,
        )


modes.register(
    Mode(
        long_option="discover",
        short_option="I",
        handler_function=mode_discover,
        argument=True,
        argument_descr="[-I] HOST1 HOST2...",
        argument_optional=True,
        short_help="Find new services",
        long_help=[
            "Make Check_MK behave as monitoring plug-ins that checks if an "
            "inventory would find new or vanished services for the host. "
            "If configured to do so, this will queue those hosts for automatic "
            "autodiscovery",
            "Can be restricted to certain check types. Write '--checks df -I' if "
            "you just want to look for new filesystems. Use 'cmk -L' for a "
            "list of all check types.",
            "Can also be restricted to only discovering new host labels. "
            "Use: '--only-host-labels' or '-L' ",
            "-II does the same as -I but deletes all existing checks of the "
            "specified types and hosts.",
        ],
        sub_options=[
            *_FETCHER_OPTIONS,
            _SNMP_BACKEND_OPTION,
            Option(
                long_option="discover",
                short_option="I",
                short_help="Delete existing services before starting discovery",
                count=True,
            ),
            _option_sections,
            _get_plugins_option(CheckPluginName),
            _option_detect_plugins,
            Option(
                long_option="only-host-labels",
                short_option="L",
                short_help="Restrict discovery to host labels only",
            ),
        ],
    )
)

# .
#   .--check---------------------------------------------------------------.
#   |                           _               _                          |
#   |                       ___| |__   ___  ___| | __                      |
#   |                      / __| '_ \ / _ \/ __| |/ /                      |
#   |                     | (__| | | |  __/ (__|   <                       |
#   |                      \___|_| |_|\___|\___|_|\_\                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'

_CheckingOptions = TypedDict(
    "_CheckingOptions",
    {
        "cache": Literal[True],
        "no-cache": Literal[True],
        "no-tcp": Literal[True],
        "usewalk": Literal[True],
        "no-submit": bool,
        "perfdata": bool,
        "detect-sections": frozenset[SectionName],
        "plugins": frozenset[CheckPluginName],
        "detect-plugins": frozenset[str],
    },
    total=False,
)


def mode_check(options: _CheckingOptions, args: list[str]) -> ServiceState:
    plugins = load_checks()
    loading_result = load_config(plugins)
    return run_checking(
        plugins,
        loading_result.config_cache,
        config.make_hosts_config(loading_result.loaded_config),
        config.ServiceDependsOn(
            tag_list=loading_result.config_cache.host_tags.tag_list,
            service_dependencies=loading_result.loaded_config.service_dependencies,
        ),
        options,
        args,
        password_store_file=cmk.utils.password_store.pending_password_store_path(),
    )


# also used in precompiled host checks!
def run_checking(
    plugins: AgentBasedPlugins,
    config_cache: ConfigCache,
    hosts_config: Hosts,
    service_depends_on: Callable[[HostAddress, ServiceName], Sequence[ServiceName]],
    options: _CheckingOptions,
    args: list[str],
    *,
    password_store_file: Path,
) -> ServiceState:
    file_cache_options = _handle_fetcher_options(options)
    try:
        snmp_backend_override = parse_snmp_backend(options.get("snmp-backend"))
    except ValueError as exc:
        raise MKBailOut("Unknown SNMP backend") from exc

    # handle adhoc-check
    hostname = HostName(args[0])
    ipaddress: HostAddress | None = None
    if len(args) == 2:
        ipaddress = HostAddress(args[1])

    ip_lookup_config = config_cache.ip_lookup_config()
    ip_address_of = ip_lookup.ConfiguredIPLookup(
        ip_lookup.make_lookup_ip_address(ip_lookup_config),
        allow_empty=config_cache.hosts_config.clusters,
        error_handler=config.handle_ip_lookup_failure,
    )
    config_cache.ruleset_matcher.ruleset_optimizer.set_all_processed_hosts({hostname})
    selected_sections, run_plugin_names = _extract_plugin_selection(
        options,
        plugins.check_plugins,
        itertools.chain(plugins.agent_sections.values(), plugins.snmp_sections.values()),
        CheckPluginName,
    )

    service_name_config = config_cache.make_passive_service_name_config()
    service_configurer = config_cache.make_service_configurer(
        plugins.check_plugins, service_name_config
    )
    logger = logging.getLogger("cmk.base.checking")
    fetcher = CMKFetcher(
        config_cache,
        config_cache.fetcher_factory(service_configurer, ip_address_of),
        plugins,
        default_address_family=ip_lookup_config.default_address_family,
        file_cache_options=file_cache_options,
        force_snmp_cache_refresh=False,
        get_ip_stack_config=ip_lookup_config.ip_stack_config,
        ip_address_of=ip_address_of,
        ip_address_of_mandatory=ip_lookup.make_lookup_ip_address(ip_lookup_config),
        ip_address_of_mgmt=ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config),
        mode=(
            FetchMode.CHECKING if selected_sections is NO_SELECTION else FetchMode.FORCE_SECTIONS
        ),
        on_error=OnError.RAISE,
        selected_sections=selected_sections,
        simulation_mode=config.simulation_mode,
        snmp_backend_override=snmp_backend_override,
        password_store_file=password_store_file,
    )
    parser = CMKParser(
        config_cache.parser_factory(),
        selected_sections=selected_sections,
        keep_outdated=file_cache_options.keep_outdated,
        logger=logger,
    )
    summarizer = CMKSummarizer(
        hostname,
        config_cache.summary_config,
        override_non_ok_state=None,
    )
    dry_run = options.get("no-submit", False)
    error_handler = CheckResultErrorHandler(
        config_cache.exit_code_spec(hostname),
        host_name=hostname,
        service_name="Check_MK",
        plugin_name="mk",
        is_cluster=hostname in hosts_config.clusters,
        snmp_backend=config_cache.get_snmp_backend(hostname),
        keepalive=False,
    )

    checks_result: Sequence[ActiveCheckResult] = []
    with (
        error_handler,
        set_value_store_manager(
            ValueStoreManager(
                hostname, AllValueStoresStore(cmk.utils.paths.counters_dir / hostname)
            ),
            store_changes=not dry_run,
        ) as value_store_manager,
    ):
        console.debug(f"Checkmk version {cmk_version.__version__}")
        fetched = fetcher(hostname, ip_address=ipaddress)
        check_plugins = CheckerPluginMapper(
            config_cache,
            plugins.check_plugins,
            value_store_manager,
            logger=logger,
            clusters=hosts_config.clusters,
            rtc_package=None,
        )
        with CPUTracker(console.debug) as tracker:
            checks_result = execute_checkmk_checks(
                hostname=hostname,
                fetched=((f[0], f[1]) for f in fetched),
                parser=parser,
                summarizer=summarizer,
                section_plugins=SectionPluginMapper(
                    {**plugins.agent_sections, **plugins.snmp_sections}
                ),
                section_error_handling=lambda section_name, raw_data: create_section_crash_dump(
                    operation="parsing",
                    section_name=section_name,
                    section_content=raw_data,
                    host_name=hostname,
                    rtc_package=None,
                ),
                check_plugins=check_plugins,
                inventory_plugins=plugins.inventory_plugins,
                inventory_parameters=config_cache.inventory_parameters,
                params=config_cache.hwsw_inventory_parameters(hostname),
                services=config_cache.configured_services(
                    hostname,
                    plugins.check_plugins,
                    service_configurer,
                    service_name_config,
                    service_depends_on,
                ),
                run_plugin_names=run_plugin_names,
                get_check_period=lambda service_name,
                service_labels: config_cache.check_period_of_service(
                    hostname, service_name, service_labels
                ),
                submitter=get_submitter(
                    check_submission=config.check_submission,
                    monitoring_core=config.monitoring_core,
                    dry_run=dry_run,
                    host_name=hostname,
                    perfdata_format=("pnp" if config.perfdata_format == "pnp" else "standard"),
                    show_perfdata=options.get("perfdata", False),
                ),
                exit_spec=config_cache.exit_code_spec(hostname),
            )

        checks_result = [
            *checks_result,
            make_timing_results(
                tracker.duration,
                tuple((f[0], f[2]) for f in fetched),
                perfdata_with_times=config.check_mk_perfdata_with_times,
            ),
        ]

    if error_handler.result is not None:
        checks_result = (error_handler.result,)

    check_result = ActiveCheckResult.from_subresults(*checks_result)
    with suppress(IOError):
        sys.stdout.write(check_result.as_text() + "\n")
        sys.stdout.flush()
    return check_result.state


modes.register(
    Mode(
        long_option="check",
        handler_function=mode_check,
        argument=True,
        argument_descr="HOST [IPADDRESS]",
        argument_optional=True,
        short_help="Check all services on the given HOST",
        long_help=[
            "Execute all checks on the given HOST. Optionally you can specify "
            "a second argument, the IPADDRESS. If you don't set this, the "
            "configured IP address of the HOST is used.",
            "By default the check results are sent to the core. If you provide "
            "the option '-n', the results will not be sent to the core and the "
            "counters of the check will not be stored.",
            "You can use '-v' to see the results of the checks. Add '-p' to "
            "also see the performance data of the checks. "
            "Can be restricted to certain check types. Write '--checks df -I' if "
            "you just want to look for new filesystems. Use 'check_mk -L' for a "
            "list of all check types. Use 'tcp' for all TCP based checks and "
            "'snmp' for all SNMP based checks.",
        ],
        sub_options=[
            *_FETCHER_OPTIONS,
            _SNMP_BACKEND_OPTION,
            Option(
                long_option="no-submit",
                short_option="n",
                short_help="Do not submit results to core, do not save counters",
            ),
            Option(
                long_option="perfdata",
                short_option="p",
                short_help="Also show performance data (use with -v)",
            ),
            _option_sections,
            _get_plugins_option(CheckPluginName),
            _option_detect_plugins,
        ],
    )
)

# .
#   .--inventory-----------------------------------------------------------.
#   |             _                      _                                 |
#   |            (_)_ ____   _____ _ __ | |_ ___  _ __ _   _               |
#   |            | | '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |              |
#   |            | | | | \ V /  __/ | | | || (_) | |  | |_| |              |
#   |            |_|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |              |
#   |                                                  |___/               |
#   '----------------------------------------------------------------------'

_InventoryOptions = TypedDict(
    "_InventoryOptions",
    {
        "cache": Literal[True],
        "no-cache": Literal[True],
        "no-tcp": Literal[True],
        "usewalk": Literal[True],
        "force": bool,
        "detect-sections": frozenset[SectionName],
        "plugins": frozenset[InventoryPluginName],
        "detect-plugins": frozenset[str],
    },
    total=False,
)


def mode_inventory(options: _InventoryOptions, args: list[str]) -> None:
    file_cache_options = _handle_fetcher_options(options)
    try:
        snmp_backend_override = parse_snmp_backend(options.get("snmp-backend"))
    except ValueError as exc:
        raise MKBailOut("Unknown SNMP backend") from exc

    plugins = load_checks()
    loading_result = load_config(plugins)
    config_cache = loading_result.config_cache
    hosts_config = config.make_hosts_config(loading_result.loaded_config)
    service_name_config = config_cache.make_passive_service_name_config()
    ip_lookup_config = config_cache.ip_lookup_config()
    ip_address_of = ip_lookup.ConfiguredIPLookup(
        ip_lookup.make_lookup_ip_address(ip_lookup_config),
        allow_empty=config_cache.hosts_config.clusters,
        error_handler=config.handle_ip_lookup_failure,
    )

    if args:
        hostnames = modes.parse_hostname_list(config_cache, hosts_config, args, with_clusters=True)
        config_cache.ruleset_matcher.ruleset_optimizer.set_all_processed_hosts(set(hostnames))
        console.verbose(f"Doing HW/SW Inventory on: {', '.join(hostnames)}")
    else:
        # No hosts specified: do all hosts and force caching
        hostnames = sorted(
            {
                hn
                for hn in itertools.chain(hosts_config.hosts, hosts_config.clusters)
                if config_cache.is_active(hn) and config_cache.is_online(hn)
            }
        )
        console.verbose("Doing HW/SW Inventory on all hosts")

    if "force" in options:
        file_cache_options = dataclasses.replace(file_cache_options, keep_outdated=True)

    selected_sections, run_plugin_names = _extract_plugin_selection(
        options,
        plugins.inventory_plugins,
        itertools.chain(plugins.agent_sections.values(), plugins.snmp_sections.values()),
        InventoryPluginName,
    )
    fetcher = CMKFetcher(
        config_cache,
        config_cache.fetcher_factory(
            config_cache.make_service_configurer(plugins.check_plugins, service_name_config),
            ip_address_of,
        ),
        plugins,
        default_address_family=ip_lookup_config.default_address_family,
        file_cache_options=file_cache_options,
        force_snmp_cache_refresh=False,
        get_ip_stack_config=ip_lookup_config.ip_stack_config,
        ip_address_of=ip_address_of,
        ip_address_of_mandatory=ip_lookup.make_lookup_ip_address(ip_lookup_config),
        ip_address_of_mgmt=ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config),
        mode=(
            FetchMode.INVENTORY if selected_sections is NO_SELECTION else FetchMode.FORCE_SECTIONS
        ),
        on_error=OnError.RAISE,
        selected_sections=selected_sections,
        simulation_mode=config.simulation_mode,
        snmp_backend_override=snmp_backend_override,
        password_store_file=cmk.utils.password_store.pending_password_store_path(),
    )
    parser = CMKParser(
        config_cache.parser_factory(),
        selected_sections=selected_sections,
        keep_outdated=file_cache_options.keep_outdated,
        logger=logging.getLogger("cmk.base.inventory"),
    )

    section_plugins = SectionPluginMapper({**plugins.agent_sections, **plugins.snmp_sections})
    inventory_plugins = plugins.inventory_plugins

    inv_store = InventoryStore(cmk.utils.paths.omd_root)

    for hostname in hostnames:

        def section_error_handling(
            section_name: SectionName,
            raw_data: Sequence[object],
            host_name: HostName = hostname,
        ) -> str:
            return create_section_crash_dump(
                operation="parsing",
                section_name=section_name,
                section_content=raw_data,
                host_name=host_name,
                rtc_package=None,
            )

        parameters = config_cache.hwsw_inventory_parameters(hostname)
        raw_intervals_from_config = config_cache.inv_retention_intervals(hostname)
        summarizer = CMKSummarizer(
            hostname,
            config_cache.summary_config,
            override_non_ok_state=parameters.fail_status,
        )

        section.section_begin(hostname)
        section.section_step("Inventorizing")
        try:
            previous_tree = inv_store.load_inventory_tree(host_name=hostname)
            if hostname in hosts_config.clusters:
                check_results = inventory.inventorize_cluster(
                    config_cache.nodes(hostname),
                    parameters=parameters,
                    previous_tree=previous_tree,
                ).check_results
            else:
                check_results = inventory.inventorize_host(
                    hostname,
                    fetcher=fetcher,
                    parser=parser,
                    summarizer=summarizer,
                    inventory_parameters=config_cache.inventory_parameters,
                    section_plugins=section_plugins,
                    section_error_handling=section_error_handling,
                    inventory_plugins=inventory_plugins,
                    run_plugin_names=run_plugin_names,
                    parameters=parameters,
                    raw_intervals_from_config=raw_intervals_from_config,
                    previous_tree=previous_tree,
                ).check_results

            check_result = ActiveCheckResult.from_subresults(*check_results)
            if check_result.state:
                section.section_error(check_result.summary)
            else:
                section.section_success(check_result.summary)

        except Exception as e:
            if cmk.ccc.debug.enabled():
                raise
            section.section_error("%s" % e)
        finally:
            cmk.ccc.cleanup.cleanup_globals()


modes.register(
    Mode(
        long_option="inventory",
        short_option="i",
        handler_function=mode_inventory,
        argument=True,
        argument_descr="HOST1 HOST2...",
        argument_optional=True,
        short_help="Do a HW/SW Inventory on some or all hosts",
        long_help=[
            "Does a HW/SW Inventory for all, one or several "
            "hosts. If you add the option -f, --force then persisted sections "
            "will be used even if they are outdated."
        ],
        sub_options=[
            *_FETCHER_OPTIONS,
            _SNMP_BACKEND_OPTION,
            Option(
                long_option="force",
                short_option="f",
                short_help="Use cached agent data even if it's outdated.",
            ),
            _option_sections,
            _get_plugins_option(InventoryPluginName),
            _option_detect_plugins,
        ],
    )
)


def execute_active_check_inventory(
    host_name: HostName,
    *,
    config_cache: ConfigCache,
    hosts_config: Hosts,
    fetcher: FetcherFunction,
    parser: ParserFunction,
    summarizer: SummarizerFunction,
    section_plugins: SectionMap[SectionPlugin],
    inventory_plugins: Mapping[InventoryPluginName, InventoryPlugin],
    inventory_parameters: Callable[[HostName, InventoryPlugin], Mapping[str, object]],
    parameters: HWSWInventoryParameters,
    raw_intervals_from_config: Sequence[RawIntervalFromConfig],
) -> Sequence[ActiveCheckResult]:
    inv_store = InventoryStore(cmk.utils.paths.omd_root)
    previous_tree = inv_store.load_previous_inventory_tree(host_name=host_name)

    if host_name in hosts_config.clusters:
        result = inventory.inventorize_cluster(
            config_cache.nodes(host_name),
            parameters=parameters,
            previous_tree=previous_tree,
        )
    else:
        result = inventory.inventorize_host(
            host_name,
            fetcher=fetcher,
            parser=parser,
            summarizer=summarizer,
            inventory_parameters=inventory_parameters,
            section_plugins=section_plugins,
            section_error_handling=lambda section_name, raw_data: create_section_crash_dump(
                operation="parsing",
                section_name=section_name,
                section_content=raw_data,
                host_name=host_name,
                rtc_package=None,
            ),
            inventory_plugins=inventory_plugins,
            run_plugin_names=EVERYTHING,
            parameters=parameters,
            raw_intervals_from_config=raw_intervals_from_config,
            previous_tree=previous_tree,
        )

    inv_paths = InventoryPaths(cmk.utils.paths.omd_root)
    if result.no_data_or_files:
        AutoQueue(inv_paths.auto_dir).add(host_name)
    else:
        (AutoQueue(inv_paths.auto_dir).path / str(host_name)).unlink(missing_ok=True)

    if not (result.processing_failed or result.no_data_or_files):
        save_tree_actions = _get_save_tree_actions(
            previous_tree=previous_tree,
            inventory_tree=result.inventory_tree,
            update_result=result.update_result,
        )
        # The order of archive or save is important:
        if save_tree_actions.do_archive:
            console.verbose("Archive current inventory tree.")
            inv_store.archive_inventory_tree(host_name=host_name)
        if save_tree_actions.do_save:
            console.verbose("Save new inventory tree.")
            inv_store.save_inventory_tree(
                host_name=host_name,
                tree=result.inventory_tree,
                meta=make_meta(do_archive=save_tree_actions.do_archive),
            )

    return result.check_results


class _SaveTreeActions(NamedTuple):
    do_archive: bool
    do_save: bool


def _get_save_tree_actions(
    *,
    previous_tree: ImmutableTree,
    inventory_tree: MutableTree,
    update_result: UpdateResult,
) -> _SaveTreeActions:
    if not inventory_tree:
        # Archive current inventory tree file if it exists. Important for host inventory icon
        console.verbose("No inventory tree.")
        return _SaveTreeActions(do_archive=True, do_save=False)

    if not previous_tree:
        console.verbose("New inventory tree.")
        return _SaveTreeActions(do_archive=False, do_save=True)

    if has_changed := previous_tree != inventory_tree:
        console.verbose("Inventory tree has changed.")

    if update_result.save_tree:
        console.verbose_no_lf(str(update_result))

    return _SaveTreeActions(
        do_archive=has_changed,
        do_save=(has_changed or update_result.save_tree),
    )


def mode_inventorize_marked_hosts(options: Mapping[str, object]) -> None:
    file_cache_options = _handle_fetcher_options(options)
    try:
        snmp_backend_override = parse_snmp_backend(options.get("snmp-backend"))
    except ValueError as exc:
        raise MKBailOut("Unknown SNMP backend") from exc

    if not (queue := AutoQueue(InventoryPaths(cmk.utils.paths.omd_root).auto_dir)):
        console.verbose("Autoinventory: No hosts marked by inventory check")
        return

    plugins = load_checks()
    discovery_rulesets = extract_known_discovery_rulesets(plugins)
    config_cache = config.load(discovery_rulesets).config_cache
    service_name_config = (
        config_cache.make_passive_service_name_config()
    )  # not obvious to me why/if we *really* need this
    ip_lookup_config = config_cache.ip_lookup_config()
    ip_address_of = ip_lookup.ConfiguredIPLookup(
        ip_lookup.make_lookup_ip_address(ip_lookup_config),
        allow_empty=config_cache.hosts_config.clusters,
        error_handler=config.handle_ip_lookup_failure,
    )

    parser = CMKParser(
        config_cache.parser_factory(),
        selected_sections=NO_SELECTION,
        keep_outdated=file_cache_options.keep_outdated,
        logger=logging.getLogger("cmk.base.inventory"),
    )
    fetcher = CMKFetcher(
        config_cache,
        config_cache.fetcher_factory(
            config_cache.make_service_configurer(plugins.check_plugins, service_name_config),
            ip_address_of,
        ),
        plugins,
        default_address_family=ip_lookup_config.default_address_family,
        file_cache_options=file_cache_options,
        force_snmp_cache_refresh=False,
        get_ip_stack_config=ip_lookup_config.ip_stack_config,
        ip_address_of=ip_address_of,
        ip_address_of_mandatory=ip_lookup.make_lookup_ip_address(ip_lookup_config),
        ip_address_of_mgmt=ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config),
        mode=FetchMode.INVENTORY,
        on_error=OnError.RAISE,
        selected_sections=NO_SELECTION,
        simulation_mode=config.simulation_mode,
        snmp_backend_override=snmp_backend_override,
        password_store_file=cmk.utils.password_store.core_password_store_path(),
    )

    def summarizer(host_name: HostName) -> CMKSummarizer:
        return CMKSummarizer(
            host_name,
            config_cache.summary_config,
            override_non_ok_state=config_cache.hwsw_inventory_parameters(host_name).fail_status,
        )

    hosts_config = config_cache.hosts_config
    all_hosts = frozenset(
        itertools.chain(hosts_config.hosts, hosts_config.clusters, hosts_config.shadow_hosts)
    )
    for host_name in queue:
        if host_name not in all_hosts:
            console.verbose(f"  Removing mark '{host_name}' (host not configured")
            (queue.path / str(host_name)).unlink(missing_ok=True)

    if queue.oldest() is None:
        console.verbose("Autoinventory: No hosts marked by inventory check")
        return

    console.verbose("Autoinventory: Inventorize all hosts marked by inventory check:")
    try:
        response = livestatus.LocalConnection().query("GET hosts\nColumns: name state")
        process_hosts: Container[HostName] = {
            HostName(name) for name, state in response if state == 0
        }
    except (livestatus.MKLivestatusNotFoundError, livestatus.MKLivestatusSocketError):
        process_hosts = EVERYTHING

    section_plugins = SectionPluginMapper({**plugins.agent_sections, **plugins.snmp_sections})

    start = time.monotonic()
    limit = 120
    message = f"  Timeout of {limit} seconds reached. Let's do the remaining hosts next time."

    try:
        with Timeout(limit + 10, message=message):
            for host_name in queue:
                if time.monotonic() > start + limit:
                    raise TimeoutError(message)

                if host_name not in process_hosts:
                    continue

                execute_active_check_inventory(
                    host_name,
                    config_cache=config_cache,
                    hosts_config=hosts_config,
                    parser=parser,
                    fetcher=fetcher,
                    summarizer=summarizer(host_name),
                    section_plugins=section_plugins,
                    inventory_plugins=plugins.inventory_plugins,
                    inventory_parameters=config_cache.inventory_parameters,
                    parameters=config_cache.hwsw_inventory_parameters(host_name),
                    raw_intervals_from_config=config_cache.inv_retention_intervals(host_name),
                )
    except (MKTimeout, TimeoutError) as exc:
        console.verbose_no_lf(str(exc))


modes.register(
    Mode(
        long_option="inventorize-marked-hosts",
        handler_function=mode_inventorize_marked_hosts,
        short_help="Run inventory for hosts which previously had no tree data",
        long_help=[
            "Run actual service HW/SW Inventory on all hosts that had no tree data",
            "in the previous run",
        ],
        sub_options=[*_FETCHER_OPTIONS, _SNMP_BACKEND_OPTION],
    )
)

# .
#   .--version-------------------------------------------------------------.
#   |                                     _                                |
#   |                 __   _____ _ __ ___(_) ___  _ __                     |
#   |                 \ \ / / _ \ '__/ __| |/ _ \| '_ \                    |
#   |                  \ V /  __/ |  \__ \ | (_) | | | |                   |
#   |                   \_/ \___|_|  |___/_|\___/|_| |_|                   |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def mode_version() -> None:
    print_(
        """This is Check_MK version %s %s
Copyright (C) 2009 Mathias Kettner

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; see the file COPYING.  If not, write to
    the Free Software Foundation, Inc., 59 Temple Place - Suite 330,
    Boston, MA 02111-1307, USA.

"""
        % (
            cmk_version.__version__,
            cmk_version.edition(cmk.utils.paths.omd_root).short.upper(),
        )
    )


modes.register(
    Mode(
        long_option="version",
        short_option="V",
        handler_function=mode_version,
        short_help="Print the version of Check_MK",
    )
)

# .
#   .--help----------------------------------------------------------------.
#   |                         _          _                                 |
#   |                        | |__   ___| |_ __                            |
#   |                        | '_ \ / _ \ | '_ \                           |
#   |                        | | | |  __/ | |_) |                          |
#   |                        |_| |_|\___|_| .__/                           |
#   |                                     |_|                              |
#   '----------------------------------------------------------------------'


def mode_help() -> None:
    print_(
        """WAYS TO CALL:
%s

OPTIONS:
%s

NOTES:
%s

"""
        % (
            modes.short_help(),
            modes.general_option_help(),
            modes.long_help(),
        )
    )


modes.register(
    Mode(
        long_option="help",
        short_option="h",
        handler_function=mode_help,
        short_help="Print this help",
    )
)

# .
#   .--diagnostics---------------------------------------------------------.
#   |             _ _                             _   _                    |
#   |          __| (_) __ _  __ _ _ __   ___  ___| |_(_) ___ ___           |
#   |         / _` | |/ _` |/ _` | '_ \ / _ \/ __| __| |/ __/ __|          |
#   |        | (_| | | (_| | (_| | | | | (_) \__ \ |_| | (__\__ \          |
#   |         \__,_|_|\__,_|\__, |_| |_|\___/|___/\__|_|\___|___/          |
#   |                       |___/                                          |
#   '----------------------------------------------------------------------'


def mode_create_diagnostics_dump(options: DiagnosticsModesParameters) -> None:
    # NOTE: All the stuff is logged on this level only, which is below the default WARNING level.
    log.logger.setLevel(logging.INFO)
    cmk.base.diagnostics.create_diagnostics_dump(
        config.load(discovery_rulesets=()).loaded_config,
        cmk.utils.diagnostics.deserialize_modes_parameters(options),
    )


def _get_diagnostics_dump_sub_options() -> list[Option]:
    sub_options = [
        Option(
            long_option=OPT_LOCAL_FILES,
            short_help=(
                "Pack a list of installed, unpacked, optional files below $OMD_ROOT/local. "
                "This also includes information about installed MKPs."
            ),
        ),
        Option(
            long_option=OPT_OMD_CONFIG,
            short_help="Pack content of 'etc/omd/site.conf'",
        ),
        Option(
            long_option=OPT_CHECKMK_OVERVIEW,
            short_help="Pack HW/SW Inventory node 'Software > Applications > Checkmk'",
        ),
        Option(
            long_option=OPT_CHECKMK_CONFIG_FILES,
            short_help="Pack configuration files ('*.mk' or '*.conf') from etc/checkmk",
            argument=True,
            argument_descr="FILE,FILE...",
        ),
        Option(
            long_option=OPT_CHECKMK_LOG_FILES,
            short_help="Pack log files ('*.log' or '*.state') from var/log",
            argument=True,
            argument_descr="FILE,FILE...",
        ),
    ]

    if cmk_version.edition(cmk.utils.paths.omd_root) is not cmk_version.Edition.CRE:
        sub_options.append(
            Option(
                long_option=OPT_PERFORMANCE_GRAPHS,
                short_help=(
                    "Pack performance graphs like CPU load and utilization of Checkmk Server"
                ),
            )
        )
    return sub_options


modes.register(
    Mode(
        long_option="create-diagnostics-dump",
        handler_function=mode_create_diagnostics_dump,
        short_help="Create diagnostics dump",
        long_help=[
            "Create a dump containing information for diagnostic analysis "
            "in the folder var/check_mk/diagnostics."
        ],
        sub_options=_get_diagnostics_dump_sub_options(),
    )
)
