#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Integer,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)


def _item_spec_ups_out_load():
    return TextAscii(title=_("Phase"),
                     help=_("The identifier of the phase the power is related to."))


def _parameter_valuespec_ups_out_load():
    return Tuple(elements=[
        Integer(title=_("warning at"), unit=u"%", default_value=85),
        Integer(title=_("critical at"), unit=u"%", default_value=90),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ups_out_load",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_ups_out_load,
        parameter_valuespec=_parameter_valuespec_ups_out_load,
        title=lambda: _("Parameters for output loads of UPSs and PDUs"),
    ))
