#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
from collections.abc import Callable, Container
from functools import partial

import cmk.utils.version as cmk_version
from cmk.utils.exceptions import OnError
from cmk.utils.log import console
from cmk.utils.type_defs import CheckPluginName, EVERYTHING, HostAddress, HostName, ServiceState

from cmk.fetchers import fetch_all, Mode
from cmk.fetchers.filecache import FileCacheOptions

from cmk.checkers.checkresults import ActiveCheckResult
from cmk.checkers.submitters import Submitter
from cmk.checkers.type_defs import NO_SELECTION, SectionNameCollection

import cmk.base.agent_based.error_handling as error_handling
import cmk.base.config as config
from cmk.base.config import ConfigCache
from cmk.base.sources import make_sources

from ._checking import execute_checkmk_checks


def commandline_checking(
    host_name: HostName,
    ipaddress: HostAddress | None,
    *,
    config_cache: ConfigCache,
    file_cache_options: FileCacheOptions,
    run_plugin_names: Container[CheckPluginName] = EVERYTHING,
    selected_sections: SectionNameCollection = NO_SELECTION,
    submitter: Submitter,
    active_check_handler: Callable[[HostName, str], object],
    keepalive: bool,
    perfdata_with_times: bool,
) -> ServiceState:
    # The error handling is required for the Nagios core.
    return error_handling.check_result(
        partial(
            _commandline_checking,
            host_name,
            ipaddress,
            config_cache=config_cache,
            file_cache_options=file_cache_options,
            run_plugin_names=run_plugin_names,
            selected_sections=selected_sections,
            perfdata_with_times=perfdata_with_times,
            submitter=submitter,
        ),
        exit_spec=config_cache.exit_code_spec(host_name),
        host_name=host_name,
        service_name="Check_MK",
        plugin_name="mk",
        is_cluster=config_cache.is_cluster(host_name),
        snmp_backend=config_cache.get_snmp_backend(host_name),
        active_check_handler=active_check_handler,
        keepalive=keepalive,
    )


def _commandline_checking(
    host_name: HostName,
    ipaddress: HostAddress | None,
    *,
    config_cache: ConfigCache,
    file_cache_options: FileCacheOptions,
    run_plugin_names: Container[CheckPluginName] = EVERYTHING,
    selected_sections: SectionNameCollection = NO_SELECTION,
    perfdata_with_times: bool,
    submitter: Submitter,
) -> ActiveCheckResult:
    console.vverbose("Checkmk version %s\n", cmk_version.__version__)
    # In case of keepalive we always have an ipaddress (can be 0.0.0.0 or :: when
    # address is unknown). When called as non keepalive ipaddress may be None or
    # is already an address (2nd argument)
    if ipaddress is None and not config_cache.is_cluster(host_name):
        ipaddress = config.lookup_ip_address(config_cache, host_name)

    nodes = config_cache.nodes_of(host_name)
    if nodes is None:
        hosts = [(host_name, ipaddress)]
    else:
        hosts = [(node, config.lookup_ip_address(config_cache, node)) for node in nodes]

    fetched = fetch_all(
        itertools.chain.from_iterable(
            make_sources(
                host_name_,
                ipaddress_,
                config_cache=config_cache,
                force_snmp_cache_refresh=False,
                selected_sections=selected_sections if nodes is None else NO_SELECTION,
                on_scan_error=OnError.RAISE,
                simulation_mode=config.simulation_mode,
                file_cache_options=file_cache_options,
                file_cache_max_age=config_cache.max_cachefile_age(host_name),
            )
            for host_name_, ipaddress_ in hosts
        ),
        mode=Mode.CHECKING if selected_sections is NO_SELECTION else Mode.FORCE_SECTIONS,
    )
    return execute_checkmk_checks(
        hostname=host_name,
        config_cache=config_cache,
        fetched=fetched,
        run_plugin_names=run_plugin_names,
        selected_sections=selected_sections,
        keep_outdated=file_cache_options.keep_outdated,
        perfdata_with_times=perfdata_with_times,
        submitter=submitter,
    )
