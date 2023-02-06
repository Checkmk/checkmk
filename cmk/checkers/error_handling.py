#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable

import cmk.utils.debug
from cmk.utils.exceptions import (
    MKAgentError,
    MKFetcherError,
    MKGeneralException,
    MKIPAddressLookupError,
    MKSNMPError,
    MKTimeout,
)
from cmk.utils.type_defs import (
    AgentRawData,
    CheckPluginNameStr,
    ExitSpec,
    HostName,
    ServiceName,
    ServiceState,
)

from cmk.snmplib.type_defs import SNMPBackendEnum

from cmk.checkers import crash_reporting
from cmk.checkers.checkresults import ActiveCheckResult


def check_result(
    callback: Callable[[], ActiveCheckResult],
    *,
    exit_spec: ExitSpec,
    host_name: HostName,
    service_name: ServiceName,
    plugin_name: CheckPluginNameStr,
    is_cluster: bool,
    snmp_backend: SNMPBackendEnum,
    keepalive: bool,
) -> tuple[ServiceState, str]:
    try:
        return _handle_success(callback())
    except Exception as exc:
        return _handle_failure(
            exc,
            exit_spec,
            host_name=host_name,
            service_name=service_name,
            plugin_name=plugin_name,
            is_cluster=is_cluster,
            snmp_backend=snmp_backend,
            keepalive=keepalive,
            rtc_package=None,
        )


def _handle_success(result: ActiveCheckResult) -> tuple[ServiceState, str]:
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
    snmp_backend: SNMPBackendEnum,
    rtc_package: AgentRawData | None,
    keepalive: bool,
) -> tuple[ServiceState, str]:
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
        crash_reporting.create_check_crash_dump(
            host_name,
            service_name,
            plugin_name=plugin_name,
            plugin_kwargs={},
            is_cluster=is_cluster,
            is_enforced=False,
            snmp_backend=snmp_backend,
            rtc_package=rtc_package,
        ).replace("Crash dump:\n", "Crash dump:\\n"),
    )
