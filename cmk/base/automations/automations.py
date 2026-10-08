#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import enum
import io
import logging
import sys
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager, nullcontext, redirect_stdout
from pathlib import Path
from typing import Any, Final

import cmk.ccc.debug
from cmk import trace
from cmk.automations.internal import (
    Automation,
    AutomationID,
    AutomationResult,
    AutomationState,
    entry_point_prefixes,
    StateFactory,
)
from cmk.base import config
from cmk.ccc.exceptions import MKGeneralException, MKTimeout
from cmk.ccc.timeout import Timeout
from cmk.discover_plugins import discover_all_plugins, PluginGroup

logger = logging.getLogger(__name__)
tracer = trace.get_tracer()


class MKAutomationError(MKGeneralException):
    pass


# TODO: These are the actual process exit codes of "cmk --automation ...". We should probably add
# the "OK" case (exit code 0) here, too.
class AutomationError(enum.IntEnum):
    KNOWN_ERROR = 1
    UNKNOWN_ERROR = 2


# The engine is deliberately blind to the state type: it only ever hands a state
# back to the very handler that declared it, and the plug-in built both halves
# together. There is no single state type to name here, so Any is the honest one.
type DiscoveredAutomation = Automation[Any, AutomationResult]  # type: ignore[explicit-any]


def discover_automations() -> Iterable[DiscoveredAutomation]:
    return discover_all_plugins(
        PluginGroup.AUTOMATIONS,
        entry_point_prefixes(),
        skip_wrong_types=False,
        raise_errors=True,
    ).plugins.values()


class Automations:
    """Hold the automations and the states they run against.

    A state is built by its factory the first time an automation naming that
    factory runs, and then kept, so that a long-lived engine (the automation
    helper) only has to :meth:`update` it. A short-lived one (``cmk --automation``)
    builds the single state its command needs and nothing else.
    """

    def __init__(self, plugins: Iterable[DiscoveredAutomation]) -> None:
        super().__init__()
        self._automations: Final[Mapping[AutomationID, DiscoveredAutomation]] = {
            automation.name: automation for automation in plugins
        }
        self._states_by_factory: Final[dict[StateFactory[AutomationState], AutomationState]] = {}
        self._arguments: tuple[Path, Mapping[str, object]] | None = None

    def wants_configuration_lock(self, cmd: AutomationID) -> bool:
        """Whether the configuration must be read under lock for this automation."""
        return (automation := self._automations.get(cmd)) is not None and (
            automation.lock_configuration
        )

    def update(self, omd_root: Path, raw_config: Mapping[str, object]) -> None:
        """Hand the new arguments to every state that exists.

        Must be called before the first automation is executed. States that were
        never built are left alone: they will be built from the new arguments
        when they are needed.
        """
        self._arguments = (omd_root, raw_config)
        for state in self._states_by_factory.values():
            state.update(omd_root, raw_config)

    def _get_state(self, automation: DiscoveredAutomation) -> AutomationState:
        try:
            return self._states_by_factory[automation.state_factory]
        except KeyError:
            if self._arguments is None:
                raise MKAutomationError("The configuration has not been loaded")
            return self._states_by_factory.setdefault(
                automation.state_factory,
                automation.state_factory(*self._arguments),
            )

    # Called either via the CLI's "cmk --automation" mode or via the "/automation" endpoint of the
    # automation helper.
    def execute(self, cmd: AutomationID, args: list[str]) -> AutomationResult | AutomationError:
        remaining_args, timeout = self._extract_timeout_from_args(args)
        with (
            nullcontext()
            if timeout is None
            else Timeout(timeout, message="Action timed out after %s seconds." % timeout)
        ):
            return self._execute(cmd, remaining_args)

    def _execute(self, cmd: AutomationID, args: list[str]) -> AutomationResult | AutomationError:
        # TODO: Disentangle this control flow mess
        try:
            try:
                automation = self._automations[cmd]
            except KeyError:
                raise MKAutomationError(
                    f"Unknown automation command: {cmd!r}"
                    f" (available: {', '.join(sorted(self._automations))})"
                )

            state = self._get_state(automation)
            with tracer.span(f"execute_automation[{cmd}]"), _stdout_only_on_failure():
                result = automation.handler(state, args)

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


@contextmanager
def _stdout_only_on_failure() -> Iterator[None]:
    """Hold back what the handler prints, and pass it on only if the handler fails.

    On success, stdout is where "cmk --automation" writes the serialized result,
    so nothing else may reach it. On failure, what the handler printed is part of
    the error report: the callers show stdout to the user.
    """
    buffer = io.StringIO()
    try:
        with redirect_stdout(buffer):
            yield
    except BaseException:
        sys.stdout.write(buffer.getvalue())
        raise


def load_config() -> config.LoadingResult:
    with tracer.span("load_config"):
        return config.load(validate_hosts=False)
