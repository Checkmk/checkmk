#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from functools import partial
from typing import Callable, Sequence, Tuple

from cmk.utils.cpu_tracking import Snapshot
from cmk.utils.type_defs import AgentRawData, HostName, result, ServiceState

from cmk.snmplib.type_defs import SNMPRawData

from cmk.core_helpers.type_defs import SourceInfo

import cmk.base.agent_based.error_handling as error_handling
from cmk.base.config import HostConfig

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
    host_config = HostConfig.make_host_config(host_name)
    return error_handling.check_result(
        partial(execute_check_discovery, host_name, fetched=fetched),
        host_config=host_config,
        service_name="Check_MK Discovery",
        plugin_name="discover",
        active_check_handler=active_check_handler,
        keepalive=keepalive,
    )
