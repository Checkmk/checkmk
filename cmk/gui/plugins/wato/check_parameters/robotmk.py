#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import (
    Age,
    Alternative,
    Dictionary,
    FixedValue,
    ListOf,
    RegExp,
    TextInput,
    Tuple,
)


def _item_spec() -> TextInput:
    return TextInput(title=_("Test"))


def _parameter_valuespec() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "test_runtime",
                SimpleLevels(
                    Age,
                    title=_("Maximum runtime of a test run"),
                    default_levels=(0, 0),
                ),
            ),
            (
                "runtime_thresholds_keywords",
                ListOf(
                    valuespec=Tuple(
                        title=_("<b>Keyword</b> monitoring"),
                        show_titles=True,
                        orientation="horizontal",
                        elements=[
                            RegExp(
                                title=("<b>Keyword</b> pattern"),
                                allow_empty=False,
                                mode="complete",
                            ),
                            Alternative(
                                title=_("Maximum runtime of a keyword run"),
                                elements=[
                                    FixedValue(
                                        value=None,
                                        title=_("No Levels"),
                                        totext=_("Do not impose levels, always be OK"),
                                    ),
                                    Tuple(
                                        title=_("Fixed Levels"),
                                        elements=(
                                            Age(
                                                title=_("Warning at"),
                                                default_value=0,
                                                display=["minutes", "seconds"],
                                            ),
                                            Age(
                                                title=_("Critical at"),
                                                default_value=0,
                                                display=["minutes", "seconds"],
                                            ),
                                        ),
                                    ),
                                ],
                            ),
                        ],
                    ),
                    add_label=_("Add new threshold"),
                    movable=False,
                    title=_("<b>Keyword</b> thresholds"),
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="robotmk",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec,
        title=lambda: _("Robotmk Tests"),
    )
)
