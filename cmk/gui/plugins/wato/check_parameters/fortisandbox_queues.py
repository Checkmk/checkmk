#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    Integer,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)


def _parameter_valuespec_fortisandbox_queues():
    return Dictionary(elements=[
        ("length",
         Tuple(
             title=_("Levels for queue length"),
             elements=[
                 Integer(title=_("Warning at"), unit=_("files")),
                 Integer(title=_("Critical at"), unit=_("files")),
             ],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="fortisandbox_queues",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextAscii(title=_("Queue name"),),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_fortisandbox_queues,
        title=lambda: _("Fortinet FortiSandbox Queue Length"),
    ))
