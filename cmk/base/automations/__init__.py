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

import abc
import signal
import sys
import pprint
from types import FrameType  # pylint: disable=unused-import
from typing import NoReturn, Dict, Any, List, Optional  # pylint: disable=unused-import
import six

import cmk.utils.debug
from cmk.utils.exceptions import MKTimeout
from cmk.utils.plugin_loader import load_plugins
from cmk.utils.encoding import make_utf8
from cmk.utils.exceptions import MKException

import cmk.base.utils
import cmk.base.config as config
import cmk.base.console as console
import cmk.base.profiling as profiling
import cmk.base.check_api as check_api


# TODO: Inherit from MKGeneralException
class MKAutomationError(MKException):
    pass


class Automations(object):
    def __init__(self):
        # type: () -> None
        # TODO: This disable is needed because of a pylint bug. Remove one day.
        super(Automations, self).__init__()  # pylint: disable=bad-super-call
        self._automations = {}  # type: Dict[str, Automation]

    def register(self, automation):
        # type: (Automation) -> None
        if automation.cmd is None:
            raise TypeError()
        self._automations[automation.cmd] = automation

    def execute(self, cmd, args):
        # type: (str, List[str]) -> Any
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
            console.error("%s\n" % make_utf8("%s" % e))
            if cmk.utils.debug.enabled():
                raise
            return 1

        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            console.error("%s\n" % make_utf8("%s" % e))
            return 2

        finally:
            profiling.output_profile()

        if cmk.utils.debug.enabled():
            console.output(pprint.pformat(result) + "\n")
        else:
            console.output("%r\n" % (result,))

        return 0

    def _handle_generic_arguments(self, args):
        # type: (List[str]) -> None
        """Handle generic arguments (currently only the optional timeout argument)"""
        if len(args) > 1 and args[0] == "--timeout":
            args.pop(0)
            timeout = int(args.pop(0))

            if timeout:
                signal.signal(signal.SIGALRM, self._raise_automation_timeout)
                signal.alarm(timeout)

    def _raise_automation_timeout(self, signum, stackframe):
        # type: (int, Optional[FrameType]) -> NoReturn
        raise MKTimeout("Action timed out.")


class Automation(six.with_metaclass(abc.ABCMeta, object)):
    cmd = None  # type: Optional[str]
    needs_checks = False
    needs_config = False

    @abc.abstractmethod
    def execute(self, args):
        # type: (List[str]) -> Any
        raise NotImplementedError()


#
# Initialize the modes object and load all available modes
#

automations = Automations()

load_plugins(__file__, __package__)
