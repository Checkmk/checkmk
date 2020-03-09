#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Age,
    Dictionary,
    ListOf,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)


def _parameter_valuespec_snapvault():
    return Dictionary(elements=[
        (
            "lag_time",
            Tuple(
                title=_("Default levels"),
                elements=[
                    Age(title=_("Warning at")),
                    Age(title=_("Critical at")),
                ],
            ),
        ),
        ("policy_lag_time",
         ListOf(
             Tuple(
                 orientation="horizontal",
                 elements=[
                     TextAscii(title=_("Policy name")),
                     Tuple(
                         title=_("Maximum age"),
                         elements=[
                             Age(title=_("Warning at")),
                             Age(title=_("Critical at")),
                         ],
                     ),
                 ],
             ),
             title=_('Policy specific levels (Clustermode only)'),
             help=_(
                 "Here you can specify levels for different policies which overrule the levels "
                 "from the <i>Default levels</i> parameter. This setting only works in NetApp Clustermode setups."
             ),
             allow_empty=False,
         ))
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="snapvault",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextAscii(title=_("Source Path"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_snapvault,
        title=lambda: _("NetApp Snapvaults / Snapmirror Lag Time"),
    ))
