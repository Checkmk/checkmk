#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    TextAscii,
    DropdownChoice,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_local():
    return Dictionary(elements=[
        ("outcome_on_cluster",
         DropdownChoice(
             choices=[
                 ("worst", _("Worst state")),
                 ("best", _("Best state")),
             ],
             title=_("Clusters: Prefered check result of local checks"),
             help=_("If you're running local checks on clusters via clustered services rule "
                    "you can influence the check result with this rule. You can choose between "
                    "best or worst state. Default setting is worst state."),
             default_value="worst"))
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="local",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Name of local item")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_local,
        title=lambda: _("Local checks in Checkmk clusters"),
    ))
