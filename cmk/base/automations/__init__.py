#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import enum
import os
import sys
from collections.abc import Iterable
from contextlib import nullcontext, redirect_stdout, suppress
from typing import assert_never

import cmk.ccc.debug
from cmk.ccc import version as cmk_version
from cmk.ccc.exceptions import MKGeneralException, MKTimeout

from cmk.utils import log, paths
from cmk.utils.log import console
from cmk.utils.plugin_loader import import_plugins
from cmk.utils.rulesets import RuleSetName
from cmk.utils.timeout import Timeout

from cmk.automations.results import ABCAutomationResult

from cmk.checkengine.plugins import AgentBasedPlugins

from cmk.base import config, profiling

from cmk import trace

tracer = trace.get_tracer()


class MKAutomationError(MKGeneralException):
    pass


class AutomationError(enum.IntEnum):
    KNOWN_ERROR = 1
    UNKNOWN_ERROR = 2


class Automations:
    def __init__(self) -> None:
        super().__init__()
        self._automations: dict[str, Automation] = {}

    def register(self, automation: "Automation") -> None:
        if automation.cmd is None:
            raise TypeError()
        self._automations[automation.cmd] = automation

    def execute(
        self,
        cmd: str,
        args: list[str],
        plugins: AgentBasedPlugins | None = None,
        loading_result: config.LoadingResult | None = None,
    ) -> ABCAutomationResult | AutomationError:
        remaining_args, timeout = self._extract_timeout_from_args(args)
        with (
            nullcontext()
            if timeout is None
            else Timeout(timeout, message="Action timed out after %s seconds." % timeout)
        ):
            return self._execute(cmd, remaining_args, plugins, loading_result)

    def execute_and_write_serialized_result_to_stdout(
        self,
        cmd: str,
        args: list[str],
        plugins: AgentBasedPlugins | None = None,
        loading_result: config.LoadingResult | None = None,
    ) -> int:
        try:
            result = self.execute(
                cmd,
                args,
                plugins,
                loading_result,
            )
        finally:
            profiling.output_profile()

        match result:
            case ABCAutomationResult():
                with suppress(IOError):
                    sys.stdout.write(
                        result.serialize(cmk_version.Version.from_str(cmk_version.__version__))
                        + "\n"
                    )
                    sys.stdout.flush()
                return 0
            case AutomationError():
                return result
            case _:
                assert_never(result)

    def _execute(
        self,
        cmd: str,
        args: list[str],
        plugins: AgentBasedPlugins | None,
        loading_result: config.LoadingResult | None,
    ) -> ABCAutomationResult | AutomationError:
        try:
            try:
                automation = self._automations[cmd]
            except KeyError:
                raise MKAutomationError(
                    f"Unknown automation command: {cmd!r}"
                    f" (available: {', '.join(sorted(self._automations))})"
                )

            with tracer.span(f"execute_automation[{cmd}]"):
                result = automation.execute(args, plugins, loading_result)

        except (MKGeneralException, MKTimeout) as e:
            console.error(f"{e}", file=sys.stderr)
            if cmk.ccc.debug.enabled():
                raise
            return AutomationError.KNOWN_ERROR

        except Exception as e:
            if cmk.ccc.debug.enabled():
                raise
            console.error(f"{e}", file=sys.stderr)
            return AutomationError.UNKNOWN_ERROR

        return result

    def _extract_timeout_from_args(self, args: list[str]) -> tuple[list[str], int | None]:
        match args:
            case ["--timeout", timeout, *remaining_args]:
                return remaining_args, int(timeout)
            case _:
                return args, None


def load_plugins() -> AgentBasedPlugins:
    with (
        tracer.span("load_all_plugins"),
        redirect_stdout(open(os.devnull, "w")),
    ):
        log.setup_console_logging()
        return config.load_all_pluginX(paths.checks_dir)


def load_config(discovery_rulesets: Iterable[RuleSetName]) -> config.LoadingResult:
    with tracer.span("load_config"):
        return config.load(discovery_rulesets, validate_hosts=False)


class Automation(abc.ABC):
    cmd: str | None = None

    @abc.abstractmethod
    def execute(
        self,
        args: list[str],
        plugins: AgentBasedPlugins | None,
        loaded_config: config.LoadingResult | None,
    ) -> ABCAutomationResult: ...


#
# Initialize the modes object and load all available modes
#

automations = Automations()

import_plugins(__file__, __package__)
