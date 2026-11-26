#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import logging
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import cmk.livestatus_client as livestatus
import cmk.utils.paths
from cmk.automations.backends.helper import (
    automation_helper_enabled,
    AutomationHelperUnavailable,
    HelperExecutor,
)
from cmk.automations.internal import AutomationID
from cmk.base import config
from cmk.base.notify import (
    do_notify,
    make_ensure_nagios,
    make_notification_config,
)
from cmk.ccc import store
from cmk.ccc import version as cmk_version
from cmk.ccc.exceptions import MKGeneralException, MKTerminate, raise_mkterminate_on_sigint
from cmk.ccc.version import Edition
from cmk.ccc.version import edition as edition_of_site
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import Handler as CLIHandler
from cmk.plugins.notifications.cli.notify import (
    cli_command_notify,
    NotifyRequest,
)
from cmk.utils import timeperiod
from cmk.utils.http_proxy_config import make_http_proxy_getter

logger = logging.getLogger("cmk.base.notify")


def _notification_exit_code(returncode: object) -> CLIExitCode:
    match returncode:
        case None | 0:
            return CLIExitCode.SUCCESS
        case 1:
            return CLIExitCode.FAILURE
        case _:
            return CLIExitCode.ERROR


type _EditionOf = Callable[[Path], Edition]


type _AutomationHelperEnabled = Callable[[Path], bool]


type _ExecuteNotifyAutomation = Callable[[Sequence[str]], str]


class _Notify(Protocol):
    def __call__(
        self,
        args: Sequence[str],
        *,
        omd_root: Path,
        edition: Edition,
        log_to_stdout: bool,
        keepalive: bool,
        debug: bool,
    ) -> int | None: ...


def _execute_notify_automation(args: Sequence[str]) -> str:
    return (
        HelperExecutor()
        .execute(
            command=AutomationID("notify"),
            args=args,
            stdin="",
            timeout=None,
            for_cmk_version=cmk_version.__version__,
        )
        .output
    )


def _notify(
    args: Sequence[str],
    *,
    omd_root: Path,
    edition: Edition,
    log_to_stdout: bool,
    keepalive: bool,
    debug: bool,
) -> int | None:
    with store.lock_checkmk_configuration(cmk.utils.paths.configuration_lockfile):
        loading_result = config.load(validate_hosts=False, debug=debug)

    return do_notify(
        list(args),
        omd_root=omd_root,
        log_to_stdout=log_to_stdout,
        notification_config=make_notification_config(
            edition,
            loading_result.loaded_config,
            loading_result.config_cache.ruleset_matcher,
            loading_result.config_cache.label_manager,
        ),
        define_servicegroups=loading_result.loaded_config.define_servicegroups,
        get_http_proxy=make_http_proxy_getter(loading_result.loaded_config.http_proxies),
        ensure_nagios=make_ensure_nagios(loading_result.loaded_config.monitoring_core),
        config_contacts=loading_result.loaded_config.contacts,
        keepalive=keepalive,
        all_timeperiods=timeperiod.get_all_timeperiods(loading_result.loaded_config.timeperiods),
        timeperiods_active=timeperiod.TimeperiodActiveCoreLookup(
            livestatus.get_optional_timeperiods_active_map, logger.warning
        ),
        debug=debug,
    )


def _do_notify_via_automation(
    execute_automation: _ExecuteNotifyAutomation,
    context: CLIContext,
    *,
    log_to_stdout: bool,
    args: Sequence[str],
) -> CLIExitCode:
    try:
        output = execute_automation(["--log-to-stdout", *args] if log_to_stdout else args)
    except AutomationHelperUnavailable:
        context.logger.exception(
            "The automation-helper service is required for the notification spooler. "
            "Please make sure all site services are started."
        )
        return CLIExitCode.FAILURE
    except Exception:
        context.logger.exception("Error running automation call 'notify'")
        return CLIExitCode.FAILURE

    try:
        data = ast.literal_eval(output)
    except SyntaxError, ValueError, TypeError:
        context.logger.exception("Could not parse automation result %(output)r", {"output": output})
        return CLIExitCode.ERROR

    if isinstance(data, dict):
        if log_to_stdout:
            sys.stdout.write(data["output"])
            sys.stdout.flush()
        return _notification_exit_code(data.get("exit_code"))

    context.logger.error("Unexpected automation result format: %(data)r", {"data": data})
    return CLIExitCode.ERROR


@dataclass(frozen=True, kw_only=True)
class _NotifyCommand:
    edition_of: _EditionOf
    automation_helper_enabled: _AutomationHelperEnabled
    execute_automation: _ExecuteNotifyAutomation
    notify: _Notify

    def run(self, context: CLIContext, request: NotifyRequest) -> CLIExitCode:
        try:
            edition = self.edition_of(context.omd_root)
            community_edition = edition is Edition.COMMUNITY
            if (
                not community_edition
                and "spoolfile" in request.arguments
                and self.automation_helper_enabled(context.omd_root)
            ):
                return _do_notify_via_automation(
                    self.execute_automation,
                    context,
                    log_to_stdout=request.log_to_stdout,
                    args=request.arguments,
                )

            if keepalive := not community_edition and request.keepalive:
                raise_mkterminate_on_sigint()

            return _notification_exit_code(
                self.notify(
                    request.arguments,
                    omd_root=context.omd_root,
                    edition=edition,
                    log_to_stdout=request.log_to_stdout,
                    keepalive=keepalive,
                    debug=context.global_options.debug,
                )
            )
        except MKTerminate:
            context.logger.error("<Interrupted>")  # noqa: TRY400
            return CLIExitCode.INTERRUPTED
        except MKGeneralException as e:
            context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
            if context.global_options.debug:
                raise
            return CLIExitCode.UNKNOWN


cli_handler_notify = CLIHandler(
    command=cli_command_notify,
    run=_NotifyCommand(
        edition_of=edition_of_site,
        automation_helper_enabled=automation_helper_enabled,
        execute_automation=_execute_notify_automation,
        notify=_notify,
    ).run,
)
