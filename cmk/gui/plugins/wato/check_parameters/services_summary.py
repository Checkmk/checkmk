#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, ListOfStrings, MonitoringState


def _parameter_valuespec_services_summary():
    return Dictionary(
        title=_("Autostart Services"),
        elements=[
            (
                "ignored",
                ListOfStrings(
                    title=_("Ignored autostart services"),
                    help=_(
                        "Regular expressions matching the begining of the internal name "
                        "or the description of the service. "
                        "If no name is given then this rule will match all services. The "
                        "match is done on the <i>beginning</i> of the service name. It "
                        "is done <i>case sensitive</i>. You can do a case insensitive match "
                        "by prefixing the regular expression with <tt>(?i)</tt>. Example: "
                        "<tt>(?i).*mssql</tt> matches all services which contain <tt>MSSQL</tt> "
                        "or <tt>MsSQL</tt> or <tt>mssql</tt> or..."
                    ),
                    orientation="horizontal",
                ),
            ),
            (
                "state_if_stopped",
                MonitoringState(
                    title=_("Default state if stopped autostart services are found"),
                    default_value=0,
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="services_summary",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_services_summary,
        title=lambda: _("Windows Service Summary"),
    )
)
