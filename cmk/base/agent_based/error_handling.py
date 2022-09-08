#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Callable, Tuple

import cmk.utils.debug
import cmk.utils.version as cmk_version
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
from cmk.utils.type_defs import CheckPluginNameStr, ExitSpec, HostName, ServiceName, ServiceState

import cmk.base.crash_reporting
import cmk.base.obsolete_output as out
from cmk.base.config import HostConfig


def check_result(
    callback: Callable[[], ActiveCheckResult],
    *,
    host_config: HostConfig,
    service_name: ServiceName,
    plugin_name: CheckPluginNameStr,
) -> ServiceState:
    try:
        state, text = _handle_success(callback())
    except Exception as exc:
        state, text = _handle_failure(
            exc,
            host_config.exit_code_spec(),
            host_config=host_config,
            service_name=service_name,
            plugin_name=plugin_name,
        )
    _handle_output(text, host_config.hostname)
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
    host_config: HostConfig,
    service_name: ServiceName,
    plugin_name: CheckPluginNameStr,
) -> Tuple[ServiceState, str]:
    if isinstance(exc, MKTimeout):
        if _in_keepalive_mode():
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
            host_config=host_config,
            service_name=service_name,
            plugin_name=plugin_name,
            plugin_kwargs={},
            is_enforced=False,
        ).replace("Crash dump:\n", "Crash dump:\\n"),
    )


def _handle_output(output_text: str, hostname: HostName) -> None:
    if _in_keepalive_mode():
        import cmk.base.cee.keepalive as keepalive  # pylint: disable=no-name-in-module

        keepalive.add_active_check_result(hostname, output_text)
        console.verbose(output_text)
    else:
        out.output(output_text)


def _in_keepalive_mode() -> bool:
    if cmk_version.is_raw_edition():
        return False
    import cmk.base.cee.keepalive as keepalive  # pylint: disable=no-name-in-module

    return keepalive.enabled()
