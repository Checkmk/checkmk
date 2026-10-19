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
from collections.abc import Mapping
from pathlib import Path

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
from cmk.cli.internal import Args, CLICommand, CLIOption, GlobalOptions, Options
from cmk.utils import timeperiod
from cmk.utils.http_proxy_config import make_http_proxy_getter

logger = logging.getLogger("cmk.base.notify")


def _notify_flags(parsed: Mapping[str, object]) -> dict[str, bool]:
    return dict.fromkeys(parsed, True)


def _mode_notify(
    omd_root: Path, _global_options: GlobalOptions, parsed: Options, args: Args
) -> int:
    options = _notify_flags(parsed)
    edition = edition_of_site(omd_root)
    community_edition = edition is Edition.COMMUNITY
    if not community_edition and "spoolfile" in args:
        return (
            _do_notify_via_automation(
                options=options,
                args=list(args),
            )
            or 0
        )

    if keepalive := not community_edition and "keepalive" in options:
        raise_mkterminate_on_sigint()

    with store.lock_checkmk_configuration(cmk.utils.paths.configuration_lockfile):
        loading_result = config.load(validate_hosts=False)

    exit_status = do_notify(
        options,
        list(args),
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
    )
    return exit_status or 0


def _run_notify(omd_root: Path, global_options: GlobalOptions, options: Options, args: Args) -> int:
    try:
        return _mode_notify(omd_root, global_options, options, args)
    except MKTerminate:
        logging.getLogger("cmk.base").error("<Interrupted>")  # noqa: TRY400
        return 1
    except MKGeneralException as e:
        logging.getLogger("cmk.base").error("%(error)s", {"error": e})  # noqa: TRY400
        if global_options.debug:
            raise
        return 3


def _do_notify_via_automation(options: dict[str, bool], args: list[str]) -> int | None:
    log_to_stdout = False
    if options.get("log-to-stdout"):
        args.insert(0, "--log-to-stdout")
        log_to_stdout = True

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
        return 1
    except Exception:
        logger.exception("Error running automation call 'notify'")
        return 1

    try:
        data = ast.literal_eval(result.output)
    except SyntaxError, ValueError, TypeError:
        logger.exception("Could not parse automation result %(output)r", {"output": result.output})
        return 2

    if isinstance(data, dict):
        if log_to_stdout:
            sys.stdout.write(data["output"])
            sys.stdout.flush()
        return data.get("exit_code")

    logger.error("Unexpected automation result format: %(data)r", {"data": data})
    return 2


cli_command_notify = CLICommand(
    long_option="notify",
    handler_function=_run_notify,
    argument=True,
    argument_descr="MODE",
    argument_optional=True,
    sub_options=[
        CLIOption(
            long_option="log-to-stdout",
            short_help="Also write log messages to console",
        ),
        CLIOption(
            long_option="keepalive",
            short_help="Execute in keepalive mode (Commercial editions only)",
        ),
    ],
    short_help="Used to send notifications from core",
)
