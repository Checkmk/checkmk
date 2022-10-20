#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from functools import partial
from typing import Callable, Container, Sequence, Tuple

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

from cmk.core_helpers.type_defs import NO_SELECTION, SectionNameCollection, SourceInfo

import cmk.base.agent_based.error_handling as error_handling
from cmk.base.config import HostConfig
from cmk.base.submitters import Submitter

from ._checking import execute_checkmk_checks


def active_check_checking(
    hostname: HostName,
    *,
    submitter: Submitter,
    fetched: Sequence[
        Tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception], Snapshot]
    ],
    run_plugin_names: Container[CheckPluginName] = EVERYTHING,
    selected_sections: SectionNameCollection = NO_SELECTION,
    active_check_handler: Callable[[HostName, str], object],
    keepalive: bool,
) -> ServiceState:
    """
    See Also:
        - `commandline_checking()` to fetch the data before processing.
        - `cmk.base.discovery.active_check_discovery()` for the discovery.

    """
    host_config = HostConfig.make_host_config(hostname)
    return error_handling.check_result(
        partial(
            execute_checkmk_checks,
            hostname=hostname,
            fetched=fetched,
            run_plugin_names=run_plugin_names,
            selected_sections=selected_sections,
            submitter=submitter,
        ),
        host_config=host_config,
        service_name="Check_MK",
        plugin_name="mk",
        active_check_handler=active_check_handler,
        keepalive=keepalive,
    )
