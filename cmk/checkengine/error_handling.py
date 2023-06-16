#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import Final, Literal, TypedDict

import cmk.utils.debug
from cmk.utils.exceptions import (
    MKAgentError,
    MKFetcherError,
    MKGeneralException,
    MKIPAddressLookupError,
    MKSNMPError,
    MKTimeout,
)
from cmk.utils.hostaddress import HostName
from cmk.utils.servicename import ServiceName

from cmk.snmplib.type_defs import SNMPBackendEnum

from cmk.checkengine import crash_reporting
from cmk.checkengine.checking import CheckPluginNameStr

from .submitters import ServiceState


class ExitSpec(TypedDict, total=False):
    connection: int
    timeout: int
    exception: int
    wrong_version: int
    missing_sections: int
    specific_missing_sections: list[tuple[str, int]]
    restricted_address_mismatch: int
    legacy_pull_mode: int


class CheckResultErrorHandler:
    def __init__(
        self,
        exit_spec: ExitSpec,
        *,
        host_name: HostName,
        service_name: ServiceName,
        plugin_name: CheckPluginNameStr,
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
        self._result: tuple[ServiceState, str] | None = None

    @property
    def result(self) -> tuple[ServiceState, str] | None:
        return self._result

    def __enter__(self) -> CheckResultErrorHandler:
        return self

    def __exit__(self, type_: object, value: Exception | None, traceback: object) -> Literal[True]:
        if type_ is None:
            return True
        assert value is not None
        self._result = _handle_failure(
            value,
            self.exit_spec,
            host_name=self.host_name,
            service_name=self.service_name,
            plugin_name=self.plugin_name,
            is_cluster=self.is_cluster,
            snmp_backend=self.snmp_backend,
            keepalive=self.keepalive,
        )
        return True


def _handle_failure(
    exc: Exception,
    exit_spec: ExitSpec,
    *,
    host_name: HostName,
    service_name: ServiceName,
    plugin_name: CheckPluginNameStr,
    is_cluster: bool,
    snmp_backend: SNMPBackendEnum,
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
            rtc_package=None,
        ).replace("Crash dump:\n", "Crash dump:\\n"),
    )
