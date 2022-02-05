#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    ManualCheckParameterRulespec,
    rulespec_registry,
    RulespecGroupEnforcedServicesApplications,
)
from cmk.gui.valuespec import Integer, Percentage, TextInput, Tuple


def _item_spec_wmic_process():
    return TextInput(
        title=_("Process name for usage in the Nagios service description"),
        allow_empty=False,
    )


def _parameter_valuespec_wmic_process():
    return Tuple(
        elements=[
            TextInput(
                title=_("Name of the process"),
                allow_empty=False,
            ),
            Integer(title=_("Memory warning at"), unit="MB"),
            Integer(title=_("Memory critical at"), unit="MB"),
            Integer(title=_("Pagefile warning at"), unit="MB"),
            Integer(title=_("Pagefile critical at"), unit="MB"),
            Percentage(title=_("CPU usage warning at")),
            Percentage(title=_("CPU usage critical at")),
        ],
    )


rulespec_registry.register(
    ManualCheckParameterRulespec(
        check_group_name="wmic_process",
        group=RulespecGroupEnforcedServicesApplications,
        item_spec=_item_spec_wmic_process,
        parameter_valuespec=_parameter_valuespec_wmic_process,
        title=lambda: _("Memory and CPU of processes on Windows"),
    )
)
