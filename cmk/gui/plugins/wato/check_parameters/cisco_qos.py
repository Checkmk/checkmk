#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Sequence

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Alternative,
    Dictionary,
    DropdownChoice,
    Integer,
    Percentage,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)


def _bandwidth_alternatives() -> Sequence[Tuple]:
    return [
        Tuple(
            title=_("Percentual levels (in relation to policy speed)"),
            elements=[
                Percentage(
                    title=_("Warning at"),
                    maxvalue=1000,
                    label=_("% of port speed"),
                ),
                Percentage(
                    title=_("Critical at"),
                    maxvalue=1000,
                    label=_("% of port speed"),
                ),
            ],
        ),
        Tuple(
            title=_("Absolute levels in bits or bytes per second"),
            help=_(
                "Depending on the measurement unit (defaults to bit), the absolute levels are set "
                "in bits or bytes per second."),
            elements=[
                Integer(
                    title=_("Warning at"),
                    size=10,
                    label=_("bits / bytes per second"),
                ),
                Integer(
                    title=_("Critical at"),
                    size=10,
                    label=_("bits / bytes per second"),
                ),
            ],
        ),
    ]


def _parameter_valuespec_cisco_qos():
    return Dictionary(elements=[
        ("unit",
         DropdownChoice(
             title=_("Measurement unit"),
             help=_("Here you can specifiy the measurement unit of the network interface"),
             default_value="bit",
             choices=[
                 ("bit", _("Bits")),
                 ("byte", _("Bytes")),
             ],
         )),
        ("post",
         Alternative(
             title=_("Used bandwidth (traffic)"),
             help=_("Settings levels on the used bandwidth is optional. If you do set "
                    "levels you might also consider using averaging."),
             elements=_bandwidth_alternatives(),
         )),
        ("average",
         Integer(
             title=_("Average values"),
             help=_("By activating the computation of averages, the levels on "
                    "errors and traffic are applied to the averaged value. That "
                    "way you can make the check react only on long-time changes, "
                    "not on one-minute events."),
             unit=_("minutes"),
             minvalue=1,
         )),
        ("drop",
         Alternative(
             title=_("Number of dropped bits or bytes per second"),
             elements=_bandwidth_alternatives(),
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="cisco_qos",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextAscii(title=_("Port"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_cisco_qos,
        title=lambda: _("Cisco quality of service"),
    ))
