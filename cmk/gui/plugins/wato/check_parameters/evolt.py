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


def _item_spec_evolt():
    return TextAscii(title=_("Phase"),
                     help=_("The identifier of the phase the power is related to."))


def _parameter_valuespec_evolt():
    return Tuple(
        help=_("Voltage Levels for devices like UPS or PDUs. "
               "Several phases may be addressed independently."),
        elements=[
            Integer(title=_("warning if below"), unit="V", default_value=210),
            Integer(title=_("critical if below"), unit="V", default_value=180),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="evolt",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_evolt,
        parameter_valuespec=_parameter_valuespec_evolt,
        title=lambda: _("Voltage levels (UPS / PDU / Other Devices)"),
    ))
