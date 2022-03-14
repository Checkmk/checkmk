#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import Dictionary, ListOf, MonitoringState, TextInput


def _parameter_valuespec_netapp_instance():
    return ListOf(
        valuespec=Dictionary(
            help=_("This rule allows you to override netapp warnings"),
            elements=[
                ("name", TextInput(title=_("Warning starts with"))),
                ("state", MonitoringState(title="Set state to", default_value=1)),
            ],
            optional_keys=False,
        ),
        add_label=_("Add warning"),
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="netapp_instance",
        group=RulespecGroupCheckParametersEnvironment,
        parameter_valuespec=_parameter_valuespec_netapp_instance,
        title=lambda: _("Netapp Instance State"),
    )
)
