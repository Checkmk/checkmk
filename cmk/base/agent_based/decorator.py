#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Callable, Tuple

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
from cmk.utils.type_defs import CheckPluginNameStr, HostName, ServiceName, ServiceState

import cmk.base.config as config
import cmk.base.crash_reporting
import cmk.base.obsolete_output as out

ActiveCheckFunction = Callable[..., ActiveCheckResult]
WrappedActiveCheckFunction = Callable[..., ServiceState]


def handle_check_mk_check_result(
    check_plugin_name: CheckPluginNameStr,
    description: ServiceName,
) -> Callable[[ActiveCheckFunction], WrappedActiveCheckFunction]:
    """Decorator function used to wrap all functions used to execute the "Check_MK *" checks
    Main purpose: Equalize the exception handling of all such functions"""

    def wrap(check_func: ActiveCheckFunction) -> WrappedActiveCheckFunction:
        def wrapped_check_func(hostname: HostName, *args: Any, **kwargs: Any) -> int:
            host_config = config.get_config_cache().get_host_config(hostname)
            exit_spec = host_config.exit_code_spec()
            try:
                status, output_text = _combine_texts(check_func(hostname, *args, **kwargs))

            except MKTimeout:
                if _in_keepalive_mode():
                    raise
                status = exit_spec.get("timeout", 2)
                output_text = "Timed out\n"

            except (MKAgentError, MKFetcherError, MKSNMPError, MKIPAddressLookupError) as e:
                status = exit_spec.get("connection", 2)
                output_text = f"{e}\n"

            except MKGeneralException as e:
                status = exit_spec.get("exception", 3)
                output_text = f"{e}\n"

            except Exception:
                if cmk.utils.debug.enabled():
                    raise
                status = exit_spec.get("exception", 3)
                output_text = cmk.base.crash_reporting.create_check_crash_dump(
                    host_name=hostname,
                    service_name=description,
                    plugin_name=check_plugin_name,
                    plugin_kwargs={},
                    is_enforced=False,
                ).replace("Crash dump:\n", "Crash dump:\\n")

            if _in_keepalive_mode():
                import cmk.base.cee.keepalive as keepalive  # pylint: disable=no-name-in-module

                keepalive.add_active_check_result(hostname, output_text)
                console.verbose(output_text)
            else:
                out.output(output_text)

            return status

        return wrapped_check_func

    return wrap


def _combine_texts(result: ActiveCheckResult) -> Tuple[ServiceState, str]:
    return result.state, "\n".join(
        (
            " | ".join((result.summary, " ".join(result.metrics))),
            "".join(f"{line}\n" for line in result.details),
        )
    )


def _in_keepalive_mode() -> bool:
    if cmk_version.is_raw_edition():
        return False
    import cmk.base.cee.keepalive as keepalive  # pylint: disable=no-name-in-module

    return keepalive.enabled()
