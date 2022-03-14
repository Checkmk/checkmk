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
from cmk.gui.valuespec import Dictionary, MonitoringState, TextInput, Transform


def _oracle_instance_transform_oracle_instance_params(p):
    if "ignore_noarchivelog" in p:
        if p["ignore_noarchivelog"]:
            p["noarchivelog"] = 0
        del p["ignore_noarchivelog"]
    if "uptime_min" in p:
        del p["uptime_min"]
    return p


def _parameter_valuespec_oracle_instance():
    return Transform(
        valuespec=Dictionary(
            title=_("Consider state of Archivelogmode: "),
            elements=[
                (
                    "archivelog",
                    MonitoringState(
                        default_value=0,
                        title=_("State in case of Archivelogmode is enabled: "),
                    ),
                ),
                (
                    "noarchivelog",
                    MonitoringState(
                        default_value=1,
                        title=_("State in case of Archivelogmode is disabled: "),
                    ),
                ),
                (
                    "forcelogging",
                    MonitoringState(
                        default_value=0,
                        title=_("State in case of Force Logging is enabled: "),
                    ),
                ),
                (
                    "noforcelogging",
                    MonitoringState(
                        default_value=1,
                        title=_("State in case of Force Logging is disabled: "),
                    ),
                ),
                (
                    "logins",
                    MonitoringState(
                        default_value=2,
                        title=_("State in case of logins are not possible: "),
                    ),
                ),
                (
                    "primarynotopen",
                    MonitoringState(
                        default_value=2,
                        title=_("State in case of Database is PRIMARY and not OPEN: "),
                    ),
                ),
            ],
        ),
        forth=_oracle_instance_transform_oracle_instance_params,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="oracle_instance",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Database SID"), size=12, allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_oracle_instance,
        title=lambda: _("Oracle Instance"),
    )
)
