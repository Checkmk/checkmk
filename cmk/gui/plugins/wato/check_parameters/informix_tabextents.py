#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    Integer,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_informix_tabextents():
    return Dictionary(elements=[
        ("levels",
         Tuple(
             title=_("Levels for number of table extents"),
             help=
             _("You can set a limit to the number of table extents for Informix Database application"
              ),
             elements=[
                 Integer(title=_("Warning at"), default_value=40),
                 Integer(title=_("Critical at"), default_value=70),
             ],
         )),
    ])


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="informix_tabextents",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_informix_tabextents,
        title=lambda: _("Informix Table Extents"),
    ))
