#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Dictionary, Integer


def _parameter_valuespec_disk_failures() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "levels",
                SimpleLevels(
                    spec=Integer,
                    title=_("Number of disk failures"),
                    default_levels=(1, 2),
                ),
            ),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="disk_failures",
        group=RulespecGroupCheckParametersStorage,
        parameter_valuespec=_parameter_valuespec_disk_failures,
        title=lambda: _("Number of disk failures"),
    )
)
