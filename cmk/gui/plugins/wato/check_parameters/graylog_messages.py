#!/usr/bin/env python
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


def _parameter_valuespec_graylog_messages():
    return Dictionary(elements=[
        ("msgs_upper",
         Tuple(
             title=_("Total message count upper levels"),
             elements=[
                 Integer(title=_("Warning at")),
                 Integer(title=_("Critical at")),
             ],
         )),
        ("msgs_lower",
         Tuple(
             title=_("Total message count lower levels"),
             elements=[
                 Integer(title=_("Warning if below")),
                 Integer(title=_("Critical if below")),
             ],
         )),
        ("msgs_avg",
         Integer(
             title=_("Message averaging"),
             help=_("By activating averaging, Check_MK will compute the average of "
                    "the message count over a given interval. If you define "
                    "alerting levels then these will automatically be applied on the "
                    "averaged value. This helps to mask out short peaks. "),
             unit=_("minutes"),
             minvalue=1,
             default_value=30,
         )),
        ("msgs_avg_upper",
         Tuple(
             title=_("Average message count upper levels"),
             elements=[
                 Integer(title=_("Warning at")),
                 Integer(title=_("Critical at")),
             ],
         )),
        ("msgs_avg_lower",
         Tuple(
             title=_("Average message count lower levels"),
             elements=[
                 Integer(title=_("Warning if below")),
                 Integer(title=_("Critical if below")),
             ],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="graylog_messages",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_graylog_messages,
        title=lambda: _("Graylog messages"),
    ))
