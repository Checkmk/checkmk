#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
import os
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from contextlib import nullcontext, redirect_stdout
from dataclasses import dataclass

import cmk.ccc.debug
from cmk import trace
from cmk.automations.results import ABCAutomationResult
from cmk.automations.types import AutomationID
from cmk.base import config
from cmk.base.configlib.loaded_config import LoadedConfigFragment
from cmk.base.core.interface import MonitoringCore
from cmk.ccc import version as cmk_version
from cmk.ccc.exceptions import MKGeneralException, MKTimeout
from cmk.ccc.hostaddress import HostAddress
from cmk.ccc.site import SiteId
from cmk.ccc.timeout import Timeout
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.discover_plugins import discover_plugins_from_modules
from cmk.fetchers import Fetcher, FetcherTriggerFactory
from cmk.helper_interface import AgentRawData
from cmk.snmplib import SNMPPluginStore
from cmk.utils import log
from cmk.utils.labels import LabelManager, Labels
from cmk.utils.log import console
from cmk.utils.rulesets import RuleSetName
from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher

tracer = trace.get_tracer()


class MKAutomationError(MKGeneralException):
    pass


# TODO: These are the actual process exit codes of "cmk --automation ...". We should probably add
# the "OK" case (exit code 0) here, too.
class AutomationError(enum.IntEnum):
    KNOWN_ERROR = 1
    UNKNOWN_ERROR = 2


@dataclass(frozen=True, kw_only=True)
class AutomationContext:
    edition: cmk_version.Edition
    make_bake_on_restart: Callable[
        [config.LoadingResult, Sequence[HostAddress]], Callable[[], None]
    ]
    create_core: Callable[
        [
            cmk_version.Edition,
            RulesetMatcher,
            LabelManager,
            LoadedConfigFragment,
            SNMPPluginStore,
            config.ConfigCache,
            AgentBasedPlugins,
        ],
        MonitoringCore,
    ]
    make_fetcher_trigger: FetcherTriggerFactory
    make_metric_backend_fetcher: Callable[
        [
            HostAddress,
            Callable[[HostAddress], config.ObjectAttributes],
            Callable[[HostAddress], float],
        ],
        Fetcher[AgentRawData] | None,
    ]
    get_builtin_host_labels: Callable[[SiteId], Labels]
    core_performance_settings: Callable[[LoadedConfigFragment], Mapping[str, int]]


@dataclass(frozen=True)
class Automation:
    name: AutomationID
    handler: Callable[
        [
            AutomationContext,
            list[str],
            AgentBasedPlugins | None,
            config.LoadingResult | None,
        ],
        ABCAutomationResult,
    ]
    result: type[ABCAutomationResult]


class Automations:
    def __init__(self) -> None:
        super().__init__()
        self._automations: dict[AutomationID, Automation] = {}

    # TODO: There is only a single call site of this method (per edition) when constructing the
    # CheckmkBaseApp, and the call *immediately* follows the Automations() constructor. So we should
    # probably merge this method into the constructor. As it is, it looks a bit like the "empty
    # constructor" and/or "hidden dependency" anti-pattern.
    def discover(self) -> None:
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
        assert not discovery_result.errors
        self._automations.update(
            {automation.name: automation for automation in discovery_result.plugins.values()}
        )

    # Called either via the CLI's "cmk --automation" mode or via the "/automation" endpoint of the
    # automation helper.
    def execute(
        self,
        ctx: AutomationContext,
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
            return self._execute(ctx, cmd, remaining_args, plugins, loading_result)

    def _execute(
        self,
        ctx: AutomationContext,
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
                result = automation.handler(ctx, args, plugins, loading_result)

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
        return config.load_all_plugins()


def load_config(
    discovery_rulesets: Iterable[RuleSetName],
    get_builtin_host_labels: Callable[[SiteId], Labels],
    edition: cmk_version.Edition,
) -> config.LoadingResult:
    with tracer.span("load_config"):
        return config.load(
            discovery_rulesets, get_builtin_host_labels, edition, validate_hosts=False
        )
