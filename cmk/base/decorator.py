#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Callable

from six import ensure_str

import cmk.utils.version as cmk_version
import cmk.utils.debug
import cmk.utils.defines as defines
from cmk.utils.exceptions import MKGeneralException, MKTimeout, MKSNMPError, MKIPAddressLookupError
from cmk.utils.log import console

from cmk.fetchers import MKFetcherError

import cmk.base.config as config
import cmk.base.obsolete_output as out
import cmk.base.crash_reporting
from cmk.base.exceptions import MKAgentError
from cmk.utils.type_defs import CheckPluginNameStr, HostName, ServiceName


def handle_check_mk_check_result(check_plugin_name: CheckPluginNameStr,
                                 description: ServiceName) -> Callable:
    """Decorator function used to wrap all functions used to execute the "Check_MK *" checks
    Main purpose: Equalize the exception handling of all such functions"""
    def wrap(check_func: Callable) -> Callable:
        def wrapped_check_func(hostname: HostName, *args: Any, **kwargs: Any) -> int:
            host_config = config.get_config_cache().get_host_config(hostname)
            exit_spec = host_config.exit_code_spec()

            status, infotexts, long_infotexts, perfdata = 0, [], [], []

            try:
                status, infotexts, long_infotexts, perfdata = check_func(hostname, *args, **kwargs)

            except MKTimeout:
                if _in_keepalive_mode():
                    raise
                infotexts.append("Timed out")
                status = max(status, exit_spec.get("timeout", 2))

            except (MKAgentError, MKFetcherError, MKSNMPError, MKIPAddressLookupError) as e:
                infotexts.append("%s" % e)
                status = exit_spec.get("connection", 2)

            except MKGeneralException as e:
                infotexts.append("%s" % e)
                status = max(status, exit_spec.get("exception", 3))

            except Exception:
                if cmk.utils.debug.enabled():
                    raise
                crash_output = cmk.base.crash_reporting.create_check_crash_dump(
                    hostname, check_plugin_name, {}, False, description)
                infotexts.append(crash_output.replace("Crash dump:\n", "Crash dump:\\n"))
                status = max(status, exit_spec.get("exception", 3))

            # Produce the service check result output
            output_txt = "%s - %s" % (defines.short_service_state_name(status),
                                      ", ".join(infotexts))
            if perfdata:
                output_txt += " | %s" % " ".join(perfdata)
            if long_infotexts:
                output_txt = "%s\n%s" % (output_txt, "\n".join(long_infotexts))
            output_txt += "\n"

            if _in_keepalive_mode():
                if not cmk_version.is_raw_edition():
                    import cmk.base.cee.keepalive as keepalive  # pylint: disable=no-name-in-module
                else:
                    keepalive = None  # type: ignore[assignment]

                keepalive.add_active_check_result(hostname, output_txt)
                console.verbose(ensure_str(output_txt))
            else:
                out.output(ensure_str(output_txt))

            return status

        return wrapped_check_func

    return wrap


def _in_keepalive_mode() -> bool:
    if not cmk_version.is_raw_edition():
        import cmk.base.cee.keepalive as keepalive  # pylint: disable=no-name-in-module
    else:
        keepalive = None  # type: ignore[assignment]
    return bool(keepalive and keepalive.enabled())
