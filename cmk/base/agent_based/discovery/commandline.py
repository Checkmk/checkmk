#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import logging
from collections import Counter
from collections.abc import Callable, Container, Sequence
from functools import partial

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.tty as tty
from cmk.utils.check_utils import ActiveCheckResult
from cmk.utils.cpu_tracking import Snapshot
from cmk.utils.exceptions import MKGeneralException, OnError
from cmk.utils.log import console
from cmk.utils.type_defs import AgentRawData, CheckPluginName, HostAddress, HostName, ServiceState
from cmk.utils.type_defs.result import Result

from cmk.snmplib.type_defs import SNMPRawData

import cmk.core_helpers.cache
from cmk.core_helpers.cache import FileCacheOptions
from cmk.core_helpers.type_defs import Mode, NO_SELECTION, SectionNameCollection, SourceInfo

import cmk.base.agent_based.error_handling as error_handling
import cmk.base.autochecks as autochecks
import cmk.base.check_utils
import cmk.base.config as config
import cmk.base.core
import cmk.base.crash_reporting
import cmk.base.section as section
from cmk.base.agent_based.data_provider import (
    make_broker,
    parse_messages,
    ParsedSectionsBroker,
    store_piggybacked_sections,
)
from cmk.base.agent_based.utils import check_parsing_errors
from cmk.base.config import ConfigCache
from cmk.base.sources import fetch_all, make_sources

from ._discovered_services import analyse_discovered_services
from ._discovery import execute_check_discovery
from ._host_labels import analyse_node_labels

__all__ = ["commandline_discovery", "commandline_check_discovery"]


def commandline_discovery(
    arg_hostnames: set[HostName],
    *,
    config_cache: ConfigCache,
    selected_sections: SectionNameCollection,
    file_cache_options: FileCacheOptions,
    run_plugin_names: Container[CheckPluginName],
    arg_only_new: bool,
    only_host_labels: bool = False,
) -> None:
    """Implementing cmk -I and cmk -II

    This is directly called from the main option parsing code.
    The list of hostnames is already prepared by the main code.
    If it is empty then we use all hosts and switch to using cache files.
    """
    on_error = OnError.RAISE if cmk.utils.debug.enabled() else OnError.WARN
    host_names = _preprocess_hostnames(arg_hostnames, config_cache, only_host_labels)

    mode = Mode.DISCOVERY if selected_sections is NO_SELECTION else Mode.FORCE_SECTIONS

    # Now loop through all hosts
    for host_name in sorted(host_names):
        nodes = config_cache.nodes_of(host_name)
        if nodes is None:
            hosts = [(host_name, config.lookup_ip_address(host_name))]
        else:
            hosts = [(node, config.lookup_ip_address(node)) for node in nodes]

        section.section_begin(host_name)
        try:
            fetched: Sequence[
                tuple[SourceInfo, Result[AgentRawData | SNMPRawData, Exception], Snapshot]
            ] = fetch_all(
                *(
                    make_sources(
                        host_name_,
                        ip_address_,
                        config_cache=config_cache,
                        force_snmp_cache_refresh=False,
                        selected_sections=selected_sections if nodes is None else NO_SELECTION,
                        on_scan_error=on_error if nodes is None else OnError.RAISE,
                        simulation_mode=config.simulation_mode,
                        file_cache_options=file_cache_options,
                        file_cache_max_age=config.max_cachefile_age(),
                    )
                    for host_name_, ip_address_ in hosts
                ),
                mode=mode,
            )
            host_sections, _results = parse_messages(
                ((f[0], f[1]) for f in fetched),
                selected_sections=selected_sections,
                keep_outdated=file_cache_options.keep_outdated,
                logger=logging.getLogger("cmk.base.discovery"),
            )
            store_piggybacked_sections(host_sections)
            parsed_sections_broker = make_broker(host_sections)
            _commandline_discovery_on_host(
                host_name=host_name,
                config_cache=config_cache,
                parsed_sections_broker=parsed_sections_broker,
                run_plugin_names=run_plugin_names,
                only_new=arg_only_new,
                load_labels=arg_only_new,
                only_host_labels=only_host_labels,
                on_error=on_error,
            )

        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            section.section_error("%s" % e)
        finally:
            cmk.utils.cleanup.cleanup_globals()


def _preprocess_hostnames(
    arg_host_names: set[HostName],
    config_cache: ConfigCache,
    only_host_labels: bool,
) -> set[HostName]:
    """Default to all hosts and expand cluster names to their nodes"""
    if not arg_host_names:
        console.verbose(
            "Discovering %shost labels on all hosts\n"
            % ("services and " if not only_host_labels else "")
        )
        arg_host_names = config_cache.all_active_realhosts()
    else:
        console.verbose(
            "Discovering %shost labels on: %s\n"
            % ("services and " if not only_host_labels else "", ", ".join(sorted(arg_host_names)))
        )

    host_names: set[HostName] = set()
    # For clusters add their nodes to the list. Clusters itself
    # cannot be discovered but the user is allowed to specify
    # them and we do discovery on the nodes instead.
    for host_name in arg_host_names:
        if not config_cache.is_cluster(host_name):
            host_names.add(host_name)
            continue

        nodes = config_cache.nodes_of(host_name)
        if nodes is None:
            raise MKGeneralException("Invalid cluster configuration")
        host_names.update(nodes)

    return host_names


def _commandline_discovery_on_host(
    *,
    host_name: HostName,
    config_cache: ConfigCache,
    parsed_sections_broker: ParsedSectionsBroker,
    run_plugin_names: Container[CheckPluginName],
    only_new: bool,
    load_labels: bool,
    only_host_labels: bool,
    on_error: OnError,
) -> None:

    section.section_step("Analyse discovered host labels")

    host_labels = analyse_node_labels(
        host_name=host_name,
        config_cache=config_cache,
        parsed_sections_broker=parsed_sections_broker,
        load_labels=load_labels,
        save_labels=True,
        on_error=on_error,
    )

    count = len(host_labels.new) if host_labels.new else ("no new" if only_new else "no")
    section.section_success(f"Found {count} host labels")

    if only_host_labels:
        return

    section.section_step("Analyse discovered services")

    service_result = analyse_discovered_services(
        host_name=host_name,
        parsed_sections_broker=parsed_sections_broker,
        run_plugin_names=run_plugin_names,
        forget_existing=not only_new,
        keep_vanished=only_new,
        on_error=on_error,
    )

    # TODO (mo): for the labels the corresponding code is in _host_labels.
    # We should put the persisting in one place.
    autochecks.AutochecksStore(host_name).write(service_result.present)

    new_per_plugin = Counter(s.check_plugin_name for s in service_result.new)
    for name, count in sorted(new_per_plugin.items()):
        console.verbose("%s%3d%s %s\n" % (tty.green + tty.bold, count, tty.normal, name))

    count = len(service_result.new) if service_result.new else ("no new" if only_new else "no")
    section.section_success(f"Found {count} services")

    for result in check_parsing_errors(parsed_sections_broker.parsing_errors()):
        for line in result.details:
            console.warning(line)


def commandline_check_discovery(
    host_name: HostName,
    ipaddress: HostAddress | None,
    *,
    config_cache: ConfigCache,
    active_check_handler: Callable[[HostName, str], object],
    file_cache_options: FileCacheOptions,
    discovery_file_cache_max_age: int | None,
    keepalive: bool,
) -> ServiceState:
    return error_handling.check_result(
        partial(
            _commandline_check_discovery,
            host_name,
            ipaddress,
            file_cache_options=file_cache_options,
            discovery_file_cache_max_age=discovery_file_cache_max_age,
            config_cache=config_cache,
        ),
        exit_spec=config_cache.exit_code_spec(host_name),
        host_name=host_name,
        service_name="Check_MK Discovery",
        plugin_name="discover",
        is_cluster=config_cache.is_cluster(host_name),
        snmp_backend=config_cache.get_snmp_backend(host_name),
        active_check_handler=active_check_handler,
        keepalive=keepalive,
    )


def _commandline_check_discovery(
    host_name: HostName,
    ipaddress: HostAddress | None,
    *,
    file_cache_options: FileCacheOptions,
    discovery_file_cache_max_age: int | None,
    config_cache: ConfigCache,
) -> ActiveCheckResult:
    # In case of keepalive discovery we always have an ipaddress. When called as non keepalive
    # ipaddress is always None
    if ipaddress is None and not config_cache.is_cluster(host_name):
        ipaddress = config.lookup_ip_address(host_name)

    nodes = config_cache.nodes_of(host_name)
    if nodes is None:
        hosts = [(host_name, ipaddress)]
    else:
        hosts = [(node, config.lookup_ip_address(node)) for node in nodes]

    fetched = fetch_all(
        *(
            make_sources(
                host_name_,
                ipaddress_,
                config_cache=config_cache,
                force_snmp_cache_refresh=False,
                selected_sections=NO_SELECTION,
                on_scan_error=OnError.RAISE,
                simulation_mode=config.simulation_mode,
                file_cache_options=file_cache_options,
                file_cache_max_age=config.max_cachefile_age(discovery=discovery_file_cache_max_age),
            )
            for host_name_, ipaddress_ in hosts
        ),
        mode=Mode.DISCOVERY,
    )

    return execute_check_discovery(
        host_name,
        config_cache=config_cache,
        fetched=fetched,
        keep_outdated=file_cache_options.keep_outdated,
    )
