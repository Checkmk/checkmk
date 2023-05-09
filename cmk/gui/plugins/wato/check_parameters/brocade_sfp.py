#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    Float,
    TextAscii,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersStorage,
    CheckParameterRulespecWithItem,
    rulespec_registry,
)


def _parameter_valuespec_brocade_sfp():
    return Dictionary(elements=[
        ("rx_power",
         Tuple(
             title=_("Rx power level"),
             elements=[
                 Float(title=_("Critical below"), unit=_("dBm")),
                 Float(title=_("Warning below"), unit=_("dBm")),
                 Float(title=_("Warning at"), unit=_("dBm")),
                 Float(title=_("Critical at"), unit=_("dBm"))
             ],
         )),
        ("tx_power",
         Tuple(
             title=_("Tx power level"),
             elements=[
                 Float(title=_("Critical below"), unit=_("dBm")),
                 Float(title=_("Warning below"), unit=_("dBm")),
                 Float(title=_("Warning at"), unit=_("dBm")),
                 Float(title=_("Critical at"), unit=_("dBm"))
             ],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="brocade_sfp",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextAscii(title=_("Port index")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_brocade_sfp,
        title=lambda: _("Brocade SFPs"),
    ))
