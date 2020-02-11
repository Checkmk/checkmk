#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

from typing import cast, Any, Callable  # pylint: disable=unused-import

import cmk
import cmk.utils.debug
import cmk.utils.defines as defines
from cmk.utils.exceptions import MKGeneralException, MKTimeout

import cmk.base.config as config
import cmk.base.console as console
import cmk.base.crash_reporting
from cmk.base.exceptions import MKAgentError, MKSNMPError, MKIPAddressLookupError
from cmk.base.check_utils import CheckPluginName  # pylint: disable=unused-import
from cmk.base.utils import HostName, ServiceName  # pylint: disable=unused-import

if not cmk.is_raw_edition():
    import cmk.base.cee.keepalive as keepalive  # pylint: disable=no-name-in-module
else:
    keepalive = None  # type: ignore[assignment]


def handle_check_mk_check_result(check_plugin_name, description):
    # type: (CheckPluginName, ServiceName) -> Callable
    """Decorator function used to wrap all functions used to execute the "Check_MK *" checks
    Main purpose: Equalize the exception handling of all such functions"""
    def wrap(check_func):
        # type: (Callable) -> Callable
        def wrapped_check_func(hostname, *args, **kwargs):
            # type: (HostName, Any, Any) -> int
            host_config = config.get_config_cache().get_host_config(hostname)
            exit_spec = host_config.exit_code_spec()

            status, infotexts, long_infotexts, perfdata = 0, [], [], []

            try:
                status, infotexts, long_infotexts, perfdata = check_func(hostname, *args, **kwargs)

            except SystemExit:
                raise

            except MKTimeout:
                if _in_keepalive_mode():
                    raise
                infotexts.append("Timed out")
                status = max(status, cast(int, exit_spec.get("timeout", 2)))

            except (MKAgentError, MKSNMPError, MKIPAddressLookupError) as e:
                infotexts.append("%s" % e)
                status = cast(int, exit_spec.get("connection", 2))

            except MKGeneralException as e:
                infotexts.append("%s" % e)
                status = max(status, cast(int, exit_spec.get("exception", 3)))

            except Exception:
                if cmk.utils.debug.enabled():
                    raise
                crash_output = cmk.base.crash_reporting.create_check_crash_dump(
                    hostname, check_plugin_name, None, False, None, description, [])
                infotexts.append(crash_output.replace("Crash dump:\n", "Crash dump:\\n"))
                status = max(status, cast(int, exit_spec.get("exception", 3)))

            # Produce the service check result output
            output_txt = "%s - %s" % (defines.short_service_state_name(status),
                                      ", ".join(infotexts))
            if perfdata:
                output_txt += " | %s" % " ".join(perfdata)
            if long_infotexts:
                output_txt = "%s\n%s" % (output_txt, "\n".join(long_infotexts))
            output_txt += "\n"

            if _in_keepalive_mode():
                keepalive.add_keepalive_active_check_result(hostname, output_txt)
                console.verbose(output_txt.encode("utf-8"))
            else:
                console.output(output_txt.encode("utf-8"))

            return status

        return wrapped_check_func

    return wrap


def _in_keepalive_mode():
    # type: () -> bool
    return bool(keepalive and keepalive.enabled())
