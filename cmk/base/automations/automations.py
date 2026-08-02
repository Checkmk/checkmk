#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import enum
import logging
import os
from collections.abc import Callable, Iterable, Mapping
from contextlib import nullcontext, redirect_stdout
from dataclasses import dataclass
from typing import Final

import cmk.ccc.debug
from cmk import trace
from cmk.automations.results import ABCAutomationResult
from cmk.automations.types import AutomationID
from cmk.base import config
from cmk.base.base_app import CheckmkBaseApp
from cmk.ccc.exceptions import MKGeneralException, MKTimeout
from cmk.ccc.timeout import Timeout
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.discover_plugins import discover_plugins_from_modules

logger = logging.getLogger(__name__)
tracer = trace.get_tracer()


class MKAutomationError(MKGeneralException):
    pass


# TODO: These are the actual process exit codes of "cmk --automation ...". We should probably add
# the "OK" case (exit code 0) here, too.
class AutomationError(enum.IntEnum):
    KNOWN_ERROR = 1
    UNKNOWN_ERROR = 2


@dataclass(frozen=True)
class Automation:
    name: AutomationID
    handler: Callable[
        [
            CheckmkBaseApp,
            list[str],
            AgentBasedPlugins | None,
            config.LoadingResult | None,
        ],
        ABCAutomationResult,
    ]
    result: type[ABCAutomationResult]


def discover_automations() -> Iterable[Automation]:
    discovery_result = discover_plugins_from_modules(
        plugin_prefixes={Automation: "automation_"},
        module_names_by_priority=[
            # TODO: We need to get rid of this hard-coded list
            "cmk.base.automations.check_mk",
            "cmk.base.diagnostics",
            "cmk.base.notify",
            "cmk.base.nonfree.notify_automation",
            "cmk.bakery.base.automation",  # non-free
        ],
        skip_wrong_types=False,
        raise_errors=True,
    )
    return discovery_result.plugins.values()


class Automations:
    def __init__(self, plugins: Iterable[Automation]) -> None:
        super().__init__()
        self._automations: Final[Mapping[AutomationID, Automation]] = {
            automation.name: automation for automation in plugins
        }

    # Called either via the CLI's "cmk --automation" mode or via the "/automation" endpoint of the
    # automation helper.
    def execute(
        self,
        app: CheckmkBaseApp,
        cmd: AutomationID,
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
            return self._execute(app, cmd, remaining_args, plugins, loading_result)

    def _execute(
        self,
        app: CheckmkBaseApp,
        cmd: AutomationID,
        args: list[str],
        plugins: AgentBasedPlugins | None,
        loading_result: config.LoadingResult | None,
    ) -> ABCAutomationResult | AutomationError:
        # TODO: Disentangle this control flow mess
        try:
            try:
                automation = self._automations[cmd]
            except KeyError:
                raise MKAutomationError(
                    f"Unknown automation command: {cmd!r}"
                    f" (available: {', '.join(sorted(self._automations))})"
                )

            with tracer.span(f"execute_automation[{cmd}]"):
                result = automation.handler(app, args, plugins, loading_result)

        except (MKGeneralException, MKTimeout) as e:
            logger.error(  # noqa: TRY400
                "Execution of automation '%(cmd)s' failed: %(error)s", {"cmd": cmd, "error": e}
            )
            if cmk.ccc.debug.enabled():
                raise
            return AutomationError.KNOWN_ERROR

        except Exception:
            logger.exception("Execution of automation '%(cmd)s' failed", {"cmd": cmd})
            if cmk.ccc.debug.enabled():
                raise
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
        return config.load_all_plugins()


def load_config() -> config.LoadingResult:
    with tracer.span("load_config"):
        return config.load(validate_hosts=False)
