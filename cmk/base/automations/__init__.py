#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import signal
import os
import cmk.utils.log as log
from contextlib import redirect_stdout
from types import FrameType
from typing import NoReturn, Dict, Any, List, Optional

import cmk.utils.debug
from cmk.utils.exceptions import MKTimeout
from cmk.utils.plugin_loader import load_plugins
from cmk.utils.exceptions import MKException
import cmk.utils.python_printer as python_printer
from cmk.utils.log import console

import cmk.base.config as config
import cmk.base.profiling as profiling
import cmk.base.check_api as check_api
import cmk.base.obsolete_output as out


# TODO: Inherit from MKGeneralException
class MKAutomationError(MKException):
    pass


class Automations:
    def __init__(self) -> None:
        super(Automations, self).__init__()
        self._automations: Dict[str, Automation] = {}

    def register(self, automation: 'Automation') -> None:
        if automation.cmd is None:
            raise TypeError()
        self._automations[automation.cmd] = automation

    def execute(self, cmd: str, args: List[str]) -> Any:
        self._handle_generic_arguments(args)

        try:
            try:
                automation = self._automations[cmd]
            except KeyError:
                raise MKAutomationError("Automation command '%s' is not implemented." % cmd)

            if automation.needs_checks:
                with redirect_stdout(open(os.devnull, "w")):
                    log.setup_console_logging()
                    config.load_all_agent_based_plugins(check_api.get_check_api_context)

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

        out.output(python_printer.pformat(result))
        out.output('\n')

        return 0

    def _handle_generic_arguments(self, args: List[str]) -> None:
        """Handle generic arguments (currently only the optional timeout argument)"""
        if len(args) > 1 and args[0] == "--timeout":
            args.pop(0)
            timeout = int(args.pop(0))

            if timeout:
                signal.signal(signal.SIGALRM, self._raise_automation_timeout)
                signal.alarm(timeout)

    def _raise_automation_timeout(self, signum: int, stackframe: Optional[FrameType]) -> NoReturn:
        raise MKTimeout("Action timed out.")


class Automation(metaclass=abc.ABCMeta):
    cmd: Optional[str] = None
    needs_checks = False
    needs_config = False

    @abc.abstractmethod
    def execute(self, args: List[str]) -> Any:
        raise NotImplementedError()


#
# Initialize the modes object and load all available modes
#

automations = Automations()

load_plugins(__file__, __package__)
