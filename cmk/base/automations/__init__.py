#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import signal
from types import FrameType  # pylint: disable=unused-import
from typing import NoReturn, Dict, Any, List, Optional  # pylint: disable=unused-import
import six

import cmk.utils.debug
from cmk.utils.exceptions import MKTimeout
from cmk.utils.plugin_loader import load_plugins
from cmk.utils.exceptions import MKException
import cmk.utils.python_printer as python_printer

import cmk.base.config as config
import cmk.base.console as console
import cmk.base.profiling as profiling
import cmk.base.check_api as check_api


# TODO: Inherit from MKGeneralException
class MKAutomationError(MKException):
    pass


class Automations(object):  # pylint: disable=useless-object-inheritance
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
            console.error("%s\n" % e)
            if cmk.utils.debug.enabled():
                raise
            return 1

        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            console.error("%s\n" % e)
            return 2

        finally:
            profiling.output_profile()

        console.output(python_printer.pformat(result))
        console.output('\n')

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
