#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The "cmk --notify" command.

The notification engine itself is cmk.base.notify; this only turns the command
line into a call into it, or hands the work to the automation helper.
"""

import ast
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import cmk.livestatus_client as livestatus
import cmk.utils.paths
from cmk.automations.backends.helper import AutomationHelperUnavailable, HelperExecutor
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
from cmk.cli.internal import Args as CLIArgs
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.cli.internal import Reader as CLIReader
from cmk.utils import timeperiod
from cmk.utils.http_proxy_config import make_http_proxy_getter

logger = logging.getLogger("cmk.base.notify")


_LOG_TO_STDOUT_FLAG: Final = CLIFlag(
    long="log-to-stdout",
    help="Also write log messages to console",
)

_KEEPALIVE_FLAG: Final = CLIFlag(
    long="keepalive",
    help="Execute in keepalive mode (Commercial editions only)",
)


@dataclass(frozen=True, kw_only=True)
class _NotifyRequest:
    log_to_stdout: bool
    keepalive: bool


def _notify_request(options: CLIReader) -> _NotifyRequest:
    return _NotifyRequest(
        log_to_stdout=options.flag(_LOG_TO_STDOUT_FLAG),
        keepalive=options.flag(_KEEPALIVE_FLAG),
    )


def _notification_exit_code(returncode: object) -> CLIExitCode:
    match returncode:
        case None | 0:
            return CLIExitCode.SUCCESS
        case 1:
            return CLIExitCode.FAILURE
        case _:
            return CLIExitCode.ERROR


def _mode_notify(
    omd_root: Path, global_options: CLIGlobalOptions, request: _NotifyRequest, args: CLIArgs
) -> CLIExitCode:
    edition = edition_of_site(omd_root)
    community_edition = edition is Edition.COMMUNITY
    if not community_edition and "spoolfile" in args:
        return _do_notify_via_automation(log_to_stdout=request.log_to_stdout, args=list(args))

    if keepalive := not community_edition and request.keepalive:
        raise_mkterminate_on_sigint()

    with store.lock_checkmk_configuration(cmk.utils.paths.configuration_lockfile):
        loading_result = config.load(validate_hosts=False, debug=global_options.debug)

    exit_status = do_notify(
        list(args),
        log_to_stdout=request.log_to_stdout,
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
        debug=global_options.debug,
    )
    return _notification_exit_code(exit_status)


def _run_notify(context: CLIContext, request: _NotifyRequest, args: CLIArgs) -> CLIExitCode:
    try:
        return _mode_notify(context.omd_root, context.global_options, request, args)
    except MKTerminate:
        context.logger.error("<Interrupted>")  # noqa: TRY400
        return CLIExitCode.INTERRUPTED
    except MKGeneralException as e:
        context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
        if context.global_options.debug:
            raise
        return CLIExitCode.UNKNOWN


def _do_notify_via_automation(*, log_to_stdout: bool, args: list[str]) -> CLIExitCode:
    if log_to_stdout:
        args.insert(0, "--log-to-stdout")

    try:
        result = HelperExecutor().execute(
            command=AutomationID("notify"),
            args=args,
            stdin="",
            timeout=None,
            for_cmk_version=cmk_version.__version__,
        )
    except AutomationHelperUnavailable:
        logger.exception(
            "The automation-helper service is required for the notification spooler. "
            "Please make sure all site services are started."
        )
        return CLIExitCode.FAILURE
    except Exception:
        logger.exception("Error running automation call 'notify'")
        return CLIExitCode.FAILURE

    try:
        data = ast.literal_eval(result.output)
    except SyntaxError, ValueError, TypeError:
        logger.exception("Could not parse automation result %(output)r", {"output": result.output})
        return CLIExitCode.ERROR

    if isinstance(data, dict):
        if log_to_stdout:
            sys.stdout.write(data["output"])
            sys.stdout.flush()
        return _notification_exit_code(data.get("exit_code"))

    logger.error("Unexpected automation result format: %(data)r", {"data": data})
    return CLIExitCode.ERROR


cli_command_notify = CLICommand(
    name="notify",
    long="notify",
    request=_notify_request,
    handler=_run_notify,
    arguments=CLIArguments("MODE", optional=True),
    help="Used to send notifications from core",
)
