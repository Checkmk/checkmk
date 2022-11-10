#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from functools import partial
from typing import Callable, Sequence, Tuple

from cmk.utils.cpu_tracking import Snapshot
from cmk.utils.type_defs import AgentRawData, HostName, result, ServiceState

from cmk.snmplib.type_defs import SNMPBackendEnum, SNMPRawData

from cmk.core_helpers.type_defs import SourceInfo

import cmk.base.agent_based.error_handling as error_handling
import cmk.base.config as config

from ._discovery import execute_check_discovery

__all__ = ["active_check_discovery"]


def active_check_discovery(
    host_name: HostName,
    *,
    fetched: Sequence[
        Tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception], Snapshot]
    ],
    active_check_handler: Callable[[HostName, str], object],
    keepalive: bool,
) -> ServiceState:
    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(host_name)
    return error_handling.check_result(
        partial(execute_check_discovery, host_name, fetched=fetched),
        exit_spec=host_config.exit_code_spec(),
        host_name=host_config.hostname,
        service_name="Check_MK Discovery",
        plugin_name="discover",
        is_cluster=config_cache.is_cluster(host_name),
        is_inline_snmp=(
            host_config.snmp_config(host_config.hostname).snmp_backend is SNMPBackendEnum.INLINE
        ),
        active_check_handler=active_check_handler,
        keepalive=keepalive,
    )
