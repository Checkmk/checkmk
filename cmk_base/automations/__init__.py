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

import signal
import sys
import pprint
from typing import Optional  # pylint: disable=unused-import

import cmk.utils
import cmk.utils.debug
from cmk.utils.exceptions import MKTimeout
from cmk.utils.plugin_loader import load_plugins

import cmk_base.utils
import cmk_base.config as config
import cmk_base.console as console
import cmk_base.profiling as profiling
import cmk_base.check_api as check_api


# TODO: Inherit from MKGeneralException
class MKAutomationError(Exception):
    def __init__(self, reason):
        # TODO: This disable is needed because of a pylint bug. Remove one day.
        super(MKAutomationError, self).__init__(reason)  # pylint: disable=bad-super-call
        self.reason = reason

    def __str__(self):
        return self.reason


class Automations(object):
    def __init__(self):
        # TODO: This disable is needed because of a pylint bug. Remove one day.
        super(Automations, self).__init__()  # pylint: disable=bad-super-call
        self._automations = {}

    def register(self, automation):
        self._automations[automation.cmd] = automation

    def execute(self, cmd, args):
        self._handle_generic_arguments(args)

        try:
            try:
                automation = self._automations[cmd]
            except KeyError:
                raise MKAutomationError("Automation command '%s' is not implemented." % cmd)

            if automation.needs_checks:
                config.load_all_checks(check_api.get_check_api_context)

            if automation.needs_config:
                config.load(validate_hosts=False)

            result = automation.execute(args)

        except (MKAutomationError, MKTimeout) as e:
            console.error("%s\n" % cmk.utils.make_utf8("%s" % e))
            if cmk.utils.debug.enabled():
                raise
            return 1

        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            console.error("%s\n" % cmk.utils.make_utf8("%s" % e))
            return 2

        finally:
            profiling.output_profile()

        if cmk.utils.debug.enabled():
            console.output(pprint.pformat(result) + "\n")
        else:
            console.output("%r\n" % (result,))

        return 0

    # Handle generic arguments (currently only the optional timeout argument)
    def _handle_generic_arguments(self, args):
        if len(args) > 1 and args[0] == "--timeout":
            args.pop(0)
            timeout = int(args.pop(0))

            if timeout:
                MKTimeout.timeout = timeout
                signal.signal(signal.SIGALRM, self._raise_automation_timeout)
                signal.alarm(timeout)

    def _raise_automation_timeout(self, signum, stackframe):
        raise MKTimeout("Action timed out. The timeout of %d "
                        "seconds was reached." % MKTimeout.timeout)


class Automation(object):
    cmd = None  # type: Optional[str]
    needs_checks = False
    needs_config = False


#
# Initialize the modes object and load all available modes
#

automations = Automations()

load_plugins(__file__, __package__)
