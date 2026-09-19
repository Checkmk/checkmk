#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The "cmk --automation" command, the entry point of the automation calls."""

import sys
from contextlib import suppress
from pathlib import Path

import cmk.ccc.version as cmk_version
import cmk.utils.paths
from cmk import trace
from cmk.base.app import make_app
from cmk.cli.internal import Args, CLICommand, GlobalOptions, Options
from cmk.profiling import backend as profiling

tracer = trace.get_tracer()


def _mode_automation(
    omd_root: Path, _global_options: GlobalOptions, _options: Options, args: Args
) -> int:
    app = make_app(omd_root)
    from cmk.automations.types import AutomationID
    from cmk.base.automations.automations import (
        AutomationError,
        Automations,
        discover_automations,
        MKAutomationError,
    )

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
        try:
            result = automations.execute(app, name, automation_args)
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
