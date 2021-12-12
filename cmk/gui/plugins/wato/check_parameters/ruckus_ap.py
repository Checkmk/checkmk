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
from cmk.gui.valuespec import Integer, Optional, TextInput, Tuple


def _item_spec_ruckus_ap():
    return TextInput(
        title=_("Band"),
        help=_("Name of the band, e.g. 5 GHz"),
    )


def _parameter_valuespec_ruckus_ap():
    return Tuple(
        elements=[
            Optional(
                Tuple(
                    elements=[
                        Integer(title=_("Warning at"), default_value=1, unit=_("devices")),
                        Integer(title=_("Critical at"), default_value=1, unit=_("devices")),
                    ],
                ),
                sameline=True,
                label=_("Levels for <i>device time drifted</i>"),
                none_label=_("No levels set"),
                none_value=(None, None),
            ),
            Optional(
                Tuple(
                    elements=[
                        Integer(title=_("Warning at"), default_value=1, unit=_("devices")),
                        Integer(title=_("Critical at"), default_value=1, unit=_("devices")),
                    ],
                ),
                sameline=True,
                label=_("Levels for <i>device not responding</i>"),
                none_label=_("No levels set"),
                none_value=(None, None),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ruckus_ap",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_ruckus_ap,
        parameter_valuespec=_parameter_valuespec_ruckus_ap,
        title=lambda: _("Ruckus Spot Access Points"),
    )
)
