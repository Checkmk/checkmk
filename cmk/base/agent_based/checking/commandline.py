#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Container
from functools import partial

import cmk.utils.version as cmk_version
from cmk.utils.check_utils import ActiveCheckResult
from cmk.utils.exceptions import OnError
from cmk.utils.log import console
from cmk.utils.type_defs import CheckPluginName, EVERYTHING, HostAddress, HostName, ServiceState

from cmk.core_helpers.type_defs import Mode, NO_SELECTION, SectionNameCollection

import cmk.base.agent_based.error_handling as error_handling
import cmk.base.config as config
from cmk.base.sources import fetch_all, make_sources
from cmk.base.submitters import Submitter

from ._checking import execute_checkmk_checks


def commandline_checking(
    host_name: HostName,
    ipaddress: HostAddress | None,
    *,
    run_plugin_names: Container[CheckPluginName] = EVERYTHING,
    selected_sections: SectionNameCollection = NO_SELECTION,
    submitter: Submitter,
    active_check_handler: Callable[[HostName, str], object],
    keepalive: bool,
) -> ServiceState:
    # The error handling is required for the Nagios core.
    config_cache = config.get_config_cache()
    return error_handling.check_result(
        partial(
            _commandline_checking,
            host_name,
            ipaddress,
            run_plugin_names=run_plugin_names,
            selected_sections=selected_sections,
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
    run_plugin_names: Container[CheckPluginName] = EVERYTHING,
    selected_sections: SectionNameCollection = NO_SELECTION,
    submitter: Submitter,
) -> ActiveCheckResult:
    console.vverbose("Checkmk version %s\n", cmk_version.__version__)
    config_cache = config.get_config_cache()
    # In case of keepalive we always have an ipaddress (can be 0.0.0.0 or :: when
    # address is unknown). When called as non keepalive ipaddress may be None or
    # is already an address (2nd argument)
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
                force_snmp_cache_refresh=False,
                selected_sections=selected_sections if nodes is None else NO_SELECTION,
                on_scan_error=OnError.RAISE,
                simulation_mode=config.simulation_mode,
                missing_sys_description=config_cache.in_binary_hostlist(
                    host_name, config.snmp_without_sys_descr
                ),
                file_cache_max_age=config_cache.max_cachefile_age(host_name),
            )
            for host_name_, ipaddress_ in hosts
        ),
        mode=Mode.CHECKING if selected_sections is NO_SELECTION else Mode.FORCE_SECTIONS,
    )
    return execute_checkmk_checks(
        hostname=host_name,
        fetched=fetched,
        run_plugin_names=run_plugin_names,
        selected_sections=selected_sections,
        submitter=submitter,
    )
