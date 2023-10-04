#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.debug
from cmk.utils.plugin_loader import load_plugins

from cmk.commands.v1 import ActiveCheckCommand

registered_active_checks: dict[str, ActiveCheckCommand] = {}


def add_active_check_plugin(check_plugin: ActiveCheckCommand) -> None:
    # TODO: validate active check command
    registered_active_checks[check_plugin.name] = check_plugin


def load_active_checks() -> list[str]:
    errors = []
    for plugin, exception_or_module in load_plugins("cmk.base.plugins.commands.active_checks"):
        match exception_or_module:
            case BaseException() as exc:
                if cmk.utils.debug.enabled():
                    raise exc
                errors.append(f"Error in active check plugin {plugin}: {exc}\n")
            case module:
                for name, value in vars(module).items():
                    if name.startswith("active_check") and isinstance(value, ActiveCheckCommand):
                        add_active_check_plugin(value)
    return errors
