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
from cmk.gui.valuespec import (
    Alternative,
    Dictionary,
    Integer,
    Migrate,
    Percentage,
    Tuple,
)


def _parameter_valuespec_general_flash_usage():
    return Migrate(
        valuespec=Dictionary(
            elements=[
                (
                    "levels",
                    Alternative(
                        elements=[
                            Tuple(
                                title=_("Specify levels in percentage of total flash"),
                                elements=[
                                    Percentage(
                                        title=_("Warning at a usage of"),
                                        # xgettext: no-python-format
                                        label=_("% of flash"),
                                        maxvalue=None,
                                    ),
                                    Percentage(
                                        title=_("Critical at a usage of"),
                                        # xgettext: no-python-format
                                        label=_("% of flash"),
                                        maxvalue=None,
                                    ),
                                ],
                            ),
                            Tuple(
                                title=_("Specify levels in absolute usage values"),
                                elements=[
                                    Integer(title=_("Warning at"), unit=_("MB")),
                                    Integer(title=_("Critical at"), unit=_("MB")),
                                ],
                            ),
                        ]
                    ),
                ),
            ],
            optional_keys=[],
        ),
        migrate=lambda p: p if isinstance(p, dict) else {"levels": p},
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="general_flash_usage",
        group=RulespecGroupCheckParametersOperatingSystem,
        parameter_valuespec=_parameter_valuespec_general_flash_usage,
        title=lambda: _("Flash Space Usage"),
    )
)
