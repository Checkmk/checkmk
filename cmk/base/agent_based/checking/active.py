#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Callable, Container, Sequence
from functools import partial

from cmk.utils.cpu_tracking import Snapshot
from cmk.utils.type_defs import (
    AgentRawData,
    CheckPluginName,
    EVERYTHING,
    HostName,
    result,
    ServiceState,
)

from cmk.snmplib.type_defs import SNMPRawData

from cmk.fetchers import SourceInfo

from cmk.checkers.submitters import Submitter
from cmk.checkers.type_defs import NO_SELECTION, SectionNameCollection

import cmk.base.agent_based.error_handling as error_handling
from cmk.base.config import ConfigCache

from ._checking import execute_checkmk_checks


def active_check_checking(
    hostname: HostName,
    *,
    config_cache: ConfigCache,
    submitter: Submitter,
    fetched: Sequence[
        tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception], Snapshot]
    ],
    run_plugin_names: Container[CheckPluginName] = EVERYTHING,
    selected_sections: SectionNameCollection = NO_SELECTION,
    active_check_handler: Callable[[HostName, str], object],
    keepalive: bool,
    keep_outdated: bool,
    perfdata_with_times: bool,
) -> ServiceState:
    """
    See Also:
        - `commandline_checking()` to fetch the data before processing.
        - `cmk.base.discovery.active_check_discovery()` for the discovery.

    """
    return error_handling.check_result(
        partial(
            execute_checkmk_checks,
            hostname=hostname,
            config_cache=config_cache,
            fetched=fetched,
            run_plugin_names=run_plugin_names,
            keep_outdated=keep_outdated,
            selected_sections=selected_sections,
            perfdata_with_times=perfdata_with_times,
            submitter=submitter,
        ),
        exit_spec=config_cache.exit_code_spec(hostname),
        host_name=hostname,
        service_name="Check_MK",
        plugin_name="mk",
        is_cluster=config_cache.is_cluster(hostname),
        snmp_backend=config_cache.get_snmp_backend(hostname),
        active_check_handler=active_check_handler,
        keepalive=keepalive,
    )
