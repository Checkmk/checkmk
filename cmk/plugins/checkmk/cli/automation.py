#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The "cmk --automation" command, the entry point of the automation calls."""

import logging
import sys
from contextlib import nullcontext, suppress
from pathlib import Path

import cmk.ccc.version as cmk_version
import cmk.utils.paths
from cmk import trace
from cmk.cli.internal import Args, CLICommand, GlobalOptions, Options
from cmk.profiling import backend as profiling

logger = logging.getLogger(__name__)
tracer = trace.get_tracer()


def _mode_automation(
    omd_root: Path, _global_options: GlobalOptions, _options: Options, args: Args
) -> int:
    from cmk.automations.types import AutomationID
    from cmk.base import config
    from cmk.base.automations.automations import (
        AutomationError,
        Automations,
        discover_automations,
        MKAutomationError,
    )
    from cmk.ccc import debug
    from cmk.ccc.exceptions import MKGeneralException, MKTimeout
    from cmk.ccc.store import lock_checkmk_configuration

    if not args:
        raise MKAutomationError("You need to provide arguments")

    name, automation_args = AutomationID(args[0]), list(args[1:])
    automations = Automations(discover_automations())
    with tracer.span(
        f"mode_automation[{name}]",
        attributes={
            "cmk.automation.name": name,
            "cmk.automation.args": automation_args,
        },
    ):
        # Report a broken configuration the way the engine reports a failing automation.
        try:
            with (
                lock_checkmk_configuration(cmk.utils.paths.configuration_lockfile)
                if automations.wants_configuration_lock(name)
                else nullcontext()
            ):
                raw_config = config.load_raw_config(with_conf_d=True)
            automations.update(omd_root, raw_config)
        except (MKGeneralException, MKTimeout) as e:
            logger.error("Loading the configuration failed: %(error)s", {"error": e})  # noqa: TRY400
            if debug.enabled():
                raise
            return AutomationError.KNOWN_ERROR
        except Exception:
            logger.exception("Loading the configuration failed")
            if debug.enabled():
                raise
            return AutomationError.UNKNOWN_ERROR

        try:
            result = automations.execute(name, automation_args)
        finally:
            profiling.output_profile(cmk.utils.paths.profiles_dir)
        if isinstance(result, AutomationError):
            return result
        with suppress(IOError):
            sys.stdout.write(
                result.serialize(cmk_version.Version.from_str(cmk_version.__version__)) + "\n"
            )
            sys.stdout.flush()
        return 0


cli_command_automation = CLICommand(
    long_option="automation",
    handler_function=_mode_automation,
    argument=True,
    argument_descr="COMMAND...",
    argument_optional=True,
    short_help="Internal helper to invoke Check_MK actions",
)
