#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
    simple_levels,
)
from cmk.gui.valuespec import Age, Dictionary, Migrate


def _migrate(
    params: tuple[int, int] | dict[str, tuple[int, int] | None]
) -> dict[str, tuple[int, int] | None]:
    if isinstance(params, dict):
        return params
    w, c = params
    return {"levels_elapsed_time": None if (w, c) == (0, 0) else (w * 86400, c * 86400)}


def _parameter_valuespec_ups_test():
    return Migrate(
        Dictionary(
            elements=[
                (
                    "levels_elapsed_time",
                    simple_levels.SimpleLevels(
                        spec=Age,
                        title=_("Time since last UPS selftest"),
                    ),
                ),
            ],
        ),
        migrate=_migrate,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="ups_test",
        group=RulespecGroupCheckParametersEnvironment,
        parameter_valuespec=_parameter_valuespec_ups_test,
        title=lambda: _("UPS selftest"),
    )
)
