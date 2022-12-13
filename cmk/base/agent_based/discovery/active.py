#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Sequence
from functools import partial

from cmk.utils.cpu_tracking import Snapshot
from cmk.utils.type_defs import AgentRawData, HostName, result, ServiceState

from cmk.snmplib.type_defs import SNMPRawData

from cmk.core_helpers.type_defs import SourceInfo

import cmk.base.agent_based.error_handling as error_handling
from cmk.base.config import ConfigCache

from ._discovery import execute_check_discovery

__all__ = ["active_check_discovery"]


def active_check_discovery(
    host_name: HostName,
    *,
    config_cache: ConfigCache,
    fetched: Sequence[
        tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception], Snapshot]
    ],
    active_check_handler: Callable[[HostName, str], object],
    keepalive: bool,
    keep_outdated: bool,
) -> ServiceState:
    return error_handling.check_result(
        partial(
            execute_check_discovery,
            host_name,
            config_cache=config_cache,
            fetched=fetched,
            keep_outdated=keep_outdated,
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
