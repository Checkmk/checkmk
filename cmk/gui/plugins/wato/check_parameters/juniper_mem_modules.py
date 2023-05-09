#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Percentage,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)


def _item_spec_juniper_mem_modules():
    return TextAscii(
        title=_("Module Name"),
        help=_("The identificator of the module."),
    )


def _parameter_valuespec_juniper_mem_modules():
    return Tuple(
        title=_("Specify levels in percentage of total memory usage"),
        elements=[
            Percentage(title=_("Warning at a usage of"),
                       unit=_("% of RAM"),
                       default_value=80.0,
                       maxvalue=100.0),
            Percentage(title=_("Critical at a usage of"),
                       unit=_("% of RAM"),
                       default_value=90.0,
                       maxvalue=100.0)
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="juniper_mem_modules",
        group=RulespecGroupCheckParametersOperatingSystem,
        item_spec=_item_spec_juniper_mem_modules,
        parameter_valuespec=_parameter_valuespec_juniper_mem_modules,
        title=lambda: _("Juniper Modules Memory Usage"),
    ))
