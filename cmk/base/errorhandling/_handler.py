#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import Final, Literal

import cmk.ccc.debug
from cmk.ccc.exceptions import (
    MKAgentError,
    MKFetcherError,
    MKGeneralException,
    MKIPAddressLookupError,
    MKSNMPError,
    MKTimeout,
)
from cmk.ccc.hostaddress import HostName

from cmk.utils.servicename import ServiceName

from cmk.snmplib import SNMPBackendEnum

from cmk.checkengine.checkresults import ActiveCheckResult
from cmk.checkengine.exitspec import ExitSpec
from cmk.checkengine.submitters import ServiceState

from ._crash import create_check_crash_dump


class CheckResultErrorHandler:
    def __init__(
        self,
        exit_spec: ExitSpec,
        *,
        host_name: HostName,
        service_name: ServiceName,
        plugin_name: str,
        is_cluster: bool,
        snmp_backend: SNMPBackendEnum,
        keepalive: bool,
    ) -> None:
        self.exit_spec: Final = exit_spec
        self.host_name: Final = host_name
        self.service_name: Final = service_name
        self.plugin_name: Final = plugin_name
        self.is_cluster: Final = is_cluster
        self.snmp_backend: Final = snmp_backend
        self.keepalive: Final = keepalive
        # return value
        self._result: ActiveCheckResult | None = None

    @property
    def result(self) -> ActiveCheckResult | None:
        return self._result

    def __enter__(self) -> CheckResultErrorHandler:
        return self

    def __exit__(self, type_: object, value: Exception | None, traceback: object) -> Literal[True]:
        if type_ is None:
            return True
        assert value is not None
        state, summary = _handle_failure(
            value,
            self.exit_spec,
            host_name=self.host_name,
            service_name=self.service_name,
            plugin_name=self.plugin_name,
            is_cluster=self.is_cluster,
            snmp_backend=self.snmp_backend,
            keepalive=self.keepalive,
        )
        self._result = ActiveCheckResult(state=state, summary=summary)
        return True


def _handle_failure(
    exc: Exception,
    exit_spec: ExitSpec,
    *,
    host_name: HostName,
    service_name: ServiceName,
    plugin_name: str,
    is_cluster: bool,
    snmp_backend: SNMPBackendEnum,
    keepalive: bool,
) -> tuple[ServiceState, str]:
    if isinstance(exc, MKTimeout):
        if keepalive:
            raise exc
        return exit_spec.get("timeout", 2), "Timed out"

    if isinstance(exc, MKAgentError | MKFetcherError | MKSNMPError | MKIPAddressLookupError):
        return exit_spec.get("connection", 2), str(exc)

    if isinstance(exc, MKGeneralException):
        return exit_spec.get("exception", 3), str(exc)

    if cmk.ccc.debug.enabled():
        raise exc
    return (
        exit_spec.get("exception", 3),
        create_check_crash_dump(
            host_name,
            service_name,
            plugin_name=plugin_name,
            plugin_kwargs={},
            is_cluster=is_cluster,
            is_enforced=False,
            snmp_backend=snmp_backend,
            rtc_package=None,
        ).replace("Crash dump:\n", "Crash dump:\\n"),
    )
