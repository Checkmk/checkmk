#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Integer, TextInput, Tuple


def _parameter_valuespec_hpux_multipath():
    return Tuple(
        title=_("Expected path situation"),
        help=_(
            "This rules sets the expected number of various paths for a multipath LUN "
            "on HPUX servers"
        ),
        elements=[
            Integer(title=_("Number of active paths")),
            Integer(title=_("Number of standby paths")),
            Integer(title=_("Number of failed paths")),
            Integer(title=_("Number of unopen paths")),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="hpux_multipath",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextInput(title=_("WWID of the LUN")),
        parameter_valuespec=_parameter_valuespec_hpux_multipath,
        title=lambda: _("HP-UX Multipath Count"),
    )
)
