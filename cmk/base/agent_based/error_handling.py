#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from contextlib import suppress
from typing import Callable, Optional, Tuple

import cmk.utils.debug
from cmk.utils.check_utils import ActiveCheckResult
from cmk.utils.exceptions import (
    MKAgentError,
    MKFetcherError,
    MKGeneralException,
    MKIPAddressLookupError,
    MKSNMPError,
    MKTimeout,
)
from cmk.utils.log import console
from cmk.utils.type_defs import (
    AgentRawData,
    CheckPluginNameStr,
    ExitSpec,
    HostName,
    ServiceName,
    ServiceState,
)

import cmk.base.crash_reporting


def check_result(
    callback: Callable[[], ActiveCheckResult],
    *,
    exit_spec: ExitSpec,
    host_name: HostName,
    service_name: ServiceName,
    plugin_name: CheckPluginNameStr,
    is_cluster: bool,
    is_inline_snmp: bool,
    active_check_handler: Callable[[HostName, str], object],
    keepalive: bool,
) -> ServiceState:
    try:
        state, text = _handle_success(callback())
    except Exception as exc:
        state, text = _handle_failure(
            exc,
            exit_spec,
            host_name=host_name,
            service_name=service_name,
            plugin_name=plugin_name,
            is_cluster=is_cluster,
            is_inline_snmp=is_inline_snmp,
            keepalive=keepalive,
            rtc_package=None,
        )
    _handle_output(
        text,
        host_name,
        active_check_handler=active_check_handler,
        keepalive=keepalive,
    )
    return state


def _handle_success(result: ActiveCheckResult) -> Tuple[ServiceState, str]:
    return result.state, "\n".join(
        (
            " | ".join((result.summary, " ".join(result.metrics))),
            "".join(f"{line}\n" for line in result.details),
        )
    )


def _handle_failure(
    exc: Exception,
    exit_spec: ExitSpec,
    *,
    host_name: HostName,
    service_name: ServiceName,
    plugin_name: CheckPluginNameStr,
    is_cluster: bool,
    is_inline_snmp: bool,
    rtc_package: Optional[AgentRawData],
    keepalive: bool,
) -> Tuple[ServiceState, str]:
    if isinstance(exc, MKTimeout):
        if keepalive:
            raise exc
        return exit_spec.get("timeout", 2), "Timed out\n"

    if isinstance(exc, (MKAgentError, MKFetcherError, MKSNMPError, MKIPAddressLookupError)):
        return exit_spec.get("connection", 2), f"{exc}\n"

    if isinstance(exc, MKGeneralException):
        return exit_spec.get("exception", 3), f"{exc}\n"

    if cmk.utils.debug.enabled():
        raise exc
    return (
        exit_spec.get("exception", 3),
        cmk.base.crash_reporting.create_check_crash_dump(
            host_name,
            service_name,
            plugin_name=plugin_name,
            plugin_kwargs={},
            is_cluster=is_cluster,
            is_enforced=False,
            is_inline_snmp=is_inline_snmp,
            rtc_package=rtc_package,
        ).replace("Crash dump:\n", "Crash dump:\\n"),
    )


def _handle_output(
    output_text: str,
    hostname: HostName,
    *,
    active_check_handler: Callable[[HostName, str], object],
    keepalive: bool,
) -> None:
    active_check_handler(hostname, output_text)
    if keepalive:
        console.verbose(output_text)
        return
    with suppress(IOError):
        sys.stdout.write(output_text)
        sys.stdout.flush()
