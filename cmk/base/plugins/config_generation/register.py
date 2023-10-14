#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import cmk.utils.debug
from cmk.utils.plugin_loader import load_plugins

from cmk.config_generation.v1 import ActiveCheckConfig


def load_active_checks() -> tuple[Sequence[str], Mapping[str, ActiveCheckConfig]]:
    errors = []  # TODO: see if we really need to return the errors.
    # Maybe we can just either ignore or raise them.

    registered_active_checks = {}
    for plugin, exception_or_module in load_plugins(
        "cmk.base.plugins.config_generation.active_checks"
    ):
        match exception_or_module:
            case BaseException() as exc:
                if cmk.utils.debug.enabled():
                    raise exc
                errors.append(f"Error in active check plugin {plugin}: {exc}\n")
            case module:
                for name, value in vars(module).items():
                    if name.startswith("active_check") and isinstance(value, ActiveCheckConfig):
                        registered_active_checks[value.name] = value

    return errors, registered_active_checks
