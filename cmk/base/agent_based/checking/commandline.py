#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from functools import partial
from typing import Callable, Container, Optional

import cmk.utils.version as cmk_version
from cmk.utils.check_utils import ActiveCheckResult
from cmk.utils.exceptions import OnError
from cmk.utils.log import console
from cmk.utils.type_defs import CheckPluginName, EVERYTHING, HostAddress, HostName, ServiceState

from cmk.snmplib.type_defs import SNMPBackendEnum

from cmk.core_helpers.type_defs import Mode, NO_SELECTION, SectionNameCollection

import cmk.base.agent_based.error_handling as error_handling
import cmk.base.config as config
from cmk.base.sources import fetch_all, make_sources
from cmk.base.submitters import Submitter

from ._checking import execute_checkmk_checks


def commandline_checking(
    host_name: HostName,
    ipaddress: Optional[HostAddress],
    *,
    run_plugin_names: Container[CheckPluginName] = EVERYTHING,
    selected_sections: SectionNameCollection = NO_SELECTION,
    submitter: Submitter,
    active_check_handler: Callable[[HostName, str], object],
    keepalive: bool,
) -> ServiceState:
    # The error handling is required for the Nagios core.
    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(host_name)
    return error_handling.check_result(
        partial(
            _commandline_checking,
            host_name,
            ipaddress,
            run_plugin_names=run_plugin_names,
            selected_sections=selected_sections,
            submitter=submitter,
        ),
        exit_spec=host_config.exit_code_spec(),
        host_name=host_config.hostname,
        service_name="Check_MK",
        plugin_name="mk",
        is_cluster=config_cache.is_cluster(host_name),
        is_inline_snmp=(
            host_config.snmp_config(host_config.hostname).snmp_backend is SNMPBackendEnum.INLINE
        ),
        active_check_handler=active_check_handler,
        keepalive=keepalive,
    )


def _commandline_checking(
    host_name: HostName,
    ipaddress: Optional[HostAddress],
    *,
    run_plugin_names: Container[CheckPluginName] = EVERYTHING,
    selected_sections: SectionNameCollection = NO_SELECTION,
    submitter: Submitter,
) -> ActiveCheckResult:
    console.vverbose("Checkmk version %s\n", cmk_version.__version__)
    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(host_name)
    # In case of keepalive we always have an ipaddress (can be 0.0.0.0 or :: when
    # address is unknown). When called as non keepalive ipaddress may be None or
    # is already an address (2nd argument)
    if ipaddress is None and not config_cache.is_cluster(host_name):
        ipaddress = config.lookup_ip_address(host_config)

    fetched = fetch_all(
        make_sources(
            host_config,
            ipaddress,
            ip_lookup=lambda host_name: config.lookup_ip_address(
                config_cache.get_host_config(host_name)
            ),
            selected_sections=selected_sections,
            force_snmp_cache_refresh=False,
            on_scan_error=OnError.RAISE,
            simulation_mode=config.simulation_mode,
            missing_sys_description=config.get_config_cache().in_binary_hostlist(
                host_config.hostname,
                config.snmp_without_sys_descr,
            ),
            file_cache_max_age=host_config.max_cachefile_age,
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
