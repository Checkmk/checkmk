#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Dictionary, Migrate, Percentage


def _parameter_valuespec_citrix_load():
    return Migrate(
        valuespec=Dictionary(
            elements=[
                (
                    "levels",
                    SimpleLevels(
                        spec=Percentage,
                        title=_("Citrix Server load"),
                        default_levels=(85.0, 95.0),
                    ),
                )
            ],
            optional_keys=[],
        ),
        migrate=lambda p: p if isinstance(p, dict) else {"levels": (p[0] / 100.0, p[1] / 100.0)},
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="citrix_load",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_citrix_load,
        title=lambda: _("Load of Citrix Server"),
    )
)
