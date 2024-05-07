#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import Dictionary, Migrate

from .memory_arbor import DualMemoryLevels


def _parameter_valuespec_juniper_mem():
    return Migrate(
        valuespec=Dictionary(
            elements=[
                ("levels", DualMemoryLevels("memory", default_percents=(80.0, 90.0))),
            ],
            optional_keys=[],
        ),
        migrate=lambda p: p if isinstance(p, dict) else {"levels": ("perc_used", p)},
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="juniper_mem",
        group=RulespecGroupCheckParametersOperatingSystem,
        parameter_valuespec=_parameter_valuespec_juniper_mem,
        title=lambda: _("Juniper memory usage"),
    )
)
