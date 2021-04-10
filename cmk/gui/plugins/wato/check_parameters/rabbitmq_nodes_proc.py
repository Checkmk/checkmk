#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    Integer,
    Percentage,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_rabbitmq_nodes_proc():
    return Dictionary(elements=[
        ("levels",
         CascadingDropdown(title=_("Levels for erlang process usage"),
                           choices=[
                               ("fd_perc", _("Percentual levels for used processes"),
                                Tuple(elements=[
                                    Percentage(title=_("Warning at usage of"),
                                               default_value=80.0,
                                               maxvalue=None),
                                    Percentage(title=_("Critical at usage of"),
                                               default_value=90.0,
                                               maxvalue=None)
                                ],)),
                               ("fd_abs", _("Absolut level for total number of used processes"),
                                Tuple(elements=[
                                    Integer(title=_("Warning at"), unit="processes"),
                                    Integer(title=_("Critical at"), unit="processes"),
                                ],)),
                           ])),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="rabbitmq_nodes_proc",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Node name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_rabbitmq_nodes_proc,
        title=lambda: _("RabbitMQ nodes processes"),
    ))
