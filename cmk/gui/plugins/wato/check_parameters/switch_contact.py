#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import DropdownChoice, TextInput


def _parameter_valuespec_switch_contact():
    return DropdownChoice(
        help=_("This rule sets the required state of a switch contact"),
        label=_("Required switch contact state"),
        choices=[
            ("open", "Switch contact is <b>open</b>"),
            ("closed", "Switch contact is <b>closed</b>"),
            ("ignore", "Ignore switch contact state"),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="switch_contact",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=lambda: TextInput(title=_("Sensor"), allow_empty=False),
        parameter_valuespec=_parameter_valuespec_switch_contact,
        title=lambda: _("Switch contact state"),
    )
)
