#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Integer, TextInput, Tuple


def _parameter_valuespec_f5_pools():
    return Tuple(
        title=_("Minimum number of pool members"),
        elements=[
            Integer(title=_("Warning if below"), unit=_("Members ")),
            Integer(title=_("Critical if below"), unit=_("Members")),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="f5_pools",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Name of pool")),
        parameter_valuespec=_parameter_valuespec_f5_pools,
        title=lambda: _("F5 Loadbalancer Pools"),
    )
)
