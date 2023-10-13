#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.base.plugins.config_generation.register import registered_active_checks

from cmk.config_generation.v1 import ActiveCheckCommand


def get_active_check(plugin_name: str) -> ActiveCheckCommand | None:
    return registered_active_checks.get(plugin_name)


def get_all_active_check_names() -> Sequence[str]:
    return list(registered_active_checks.keys())
