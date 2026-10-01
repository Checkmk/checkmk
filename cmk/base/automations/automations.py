#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import enum
import io
import logging
import sys
from collections.abc import Callable, Iterable, Iterator, Mapping
from contextlib import contextmanager, nullcontext, redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Protocol

import cmk.ccc.debug
from cmk import trace
from cmk.automations.results import ABCAutomationResult
from cmk.automations.types import AutomationID
from cmk.base import config
from cmk.base.app import make_app
from cmk.base.base_app import CheckmkBaseApp
from cmk.ccc.exceptions import MKGeneralException, MKTimeout
from cmk.ccc.timeout import Timeout
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


class AutomationState(Protocol):
    """Whatever an automation needs to have ready before it runs.

    The engine builds it with the automation's :attr:`Automation.state_factory`,
    keeps it alive between calls and hands it the new arguments via
    :meth:`update` whenever they change.
    """

    def update(self, omd_root: Path, loading_result: config.LoadingResult | None) -> None: ...


type StateFactory[StateT: AutomationState] = Callable[[Path, config.LoadingResult | None], StateT]


@dataclass(frozen=True, kw_only=True)
class Automation[StateT: AutomationState, ResultT: ABCAutomationResult]:
    """An action the backend performs on request, selected by its :attr:`name`."""

    name: AutomationID
    state_factory: StateFactory[StateT]
    """Produce the state :attr:`handler` runs against, ready for the given arguments.

    The engine calls each distinct factory once and keeps what it returns:
    automations that name the same factory share the same state.
    """
    handler: Callable[[StateT, list[str]], ResultT]
    result: type[ResultT]
    lock_configuration: bool = False
    """Read the configuration under the configuration lock when the CLI runs this.

    The GUI holds that lock during every Setup action and calls automations from
    within them, so this must stay off for any automation it calls that way: the
    CLI would wait for a lock its own caller holds.
    """


# The engine is deliberately blind to the state type: it only ever hands a state
# back to the very handler that declared it, and the plug-in built both halves
# together. There is no single state type to name here, so Any is the honest one.
type DiscoveredAutomation = Automation[Any, ABCAutomationResult]  # type: ignore[explicit-any]


class CommonState:
    """The one state all automations share for now.

    It holds what the engine used to pass to every handler. All automations name
    this class as their factory, so the engine builds it once. Automations will
    move to states of their own, one by one.
    """

    def __init__(self, omd_root: Path, loading_result: config.LoadingResult | None) -> None:
        self.app: CheckmkBaseApp = make_app(omd_root)
        self.loading_result = loading_result

    def update(self, omd_root: Path, loading_result: config.LoadingResult | None) -> None:
        # The site, and with it the app, does not change while we run. We rebuild the
        # app anyway, so that the state is derived from its arguments alone.
        self.app = make_app(omd_root)
        self.loading_result = loading_result


def discover_automations() -> Iterable[DiscoveredAutomation]:
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
    """Hold the automations and the states they run against.

    A state is built by its factory the first time an automation naming that
    factory runs, and then kept, so that a long-lived engine (the automation
    helper) only has to :meth:`update` it. A short-lived one (``cmk --automation``)
    builds the single state its command needs and nothing else.
    """

    def __init__(
        self,
        plugins: Iterable[DiscoveredAutomation],
        *,
        omd_root: Path,
        loading_result: config.LoadingResult | None,
    ) -> None:
        super().__init__()
        self._automations: Final[Mapping[AutomationID, DiscoveredAutomation]] = {
            automation.name: automation for automation in plugins
        }
        self._states_by_factory: Final[dict[StateFactory[AutomationState], AutomationState]] = {}
        self._omd_root = omd_root
        self._loading_result = loading_result

    def wants_configuration_lock(self, cmd: AutomationID) -> bool:
        """Whether the configuration must be read under lock for this automation."""
        return (automation := self._automations.get(cmd)) is not None and (
            automation.lock_configuration
        )

    def update(self, omd_root: Path, loading_result: config.LoadingResult | None) -> None:
        """Hand the new arguments to every state that exists.

        States that were never built are left alone: they will be built from the
        new arguments when they are needed.
        """
        self._omd_root = omd_root
        self._loading_result = loading_result
        for state in self._states_by_factory.values():
            state.update(omd_root, loading_result)

    def _get_state(self, automation: DiscoveredAutomation) -> AutomationState:
        try:
            return self._states_by_factory[automation.state_factory]
        except KeyError:
            return self._states_by_factory.setdefault(
                automation.state_factory,
                automation.state_factory(self._omd_root, self._loading_result),
            )

    # Called either via the CLI's "cmk --automation" mode or via the "/automation" endpoint of the
    # automation helper.
    def execute(self, cmd: AutomationID, args: list[str]) -> ABCAutomationResult | AutomationError:
        remaining_args, timeout = self._extract_timeout_from_args(args)
        with (
            nullcontext()
            if timeout is None
            else Timeout(timeout, message="Action timed out after %s seconds." % timeout)
        ):
            return self._execute(cmd, remaining_args)

    def _execute(self, cmd: AutomationID, args: list[str]) -> ABCAutomationResult | AutomationError:
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
