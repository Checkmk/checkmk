#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Dictionary, Migrate, Percentage, TextInput


def _item_spec_juniper_mem_modules():
    return TextInput(
        title=_("Module Name"),
        help=_("The identificator of the module."),
    )


def _parameter_valuespec_juniper_mem_modules():
    return Migrate(
        valuespec=Dictionary(
            elements=[
                (
                    "levels",
                    SimpleLevels(
                        spec=Percentage,
                        title=_("Levels in percentage of total memory usage"),
                        default_levels=(80.0, 90.0),
                    ),
                ),
            ],
            optional_keys=[],
        ),
        migrate=lambda p: p if isinstance(p, dict) else {"levels": p},
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="juniper_mem_modules",
        group=RulespecGroupCheckParametersOperatingSystem,
        item_spec=_item_spec_juniper_mem_modules,
        parameter_valuespec=_parameter_valuespec_juniper_mem_modules,
        title=lambda: _("Juniper modules memory usage"),
    )
)
