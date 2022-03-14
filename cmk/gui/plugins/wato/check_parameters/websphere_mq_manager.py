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
from cmk.gui.valuespec import Dictionary, DropdownChoice, ListOf, MonitoringState, TextInput, Tuple


def _parameter_valuespec_websphere_mq_manager():
    return Dictionary(
        elements=[
            (
                "map_manager_states",
                ListOf(
                    valuespec=Tuple(
                        orientation="horizontal",
                        elements=[
                            DropdownChoice(
                                choices=[
                                    ("starting", _("Starting")),
                                    ("running", _("Running")),
                                    ("running_as_stanby", _("Running as standby")),
                                    ("running_elsewhere", _("Running elsewhere")),
                                    ("quiescing", _("Quiescing")),
                                    ("ending_immediately", _("Ending immedtiately")),
                                    ("ending_pre_emptively", _("Ending pre-emptivley")),
                                    ("ended_normally", _("Ended normally")),
                                    ("ended_immediately", _("Ended immediately")),
                                    ("ended_unexpectedly", _("Ended unexpectedly")),
                                    ("ended_pre_emptively", _("Ended pre-emptively")),
                                    ("status_not_available", _("Status not available")),
                                ],
                            ),
                            MonitoringState(),
                        ],
                    ),
                    title=_("Map manager state"),
                ),
            ),
            (
                "map_standby_states",
                ListOf(
                    valuespec=Tuple(
                        orientation="horizontal",
                        elements=[
                            DropdownChoice(
                                choices=[
                                    ("permitted", _("Permitted")),
                                    ("not_permitted", _("Not permitted")),
                                    ("not_applicable", _("Not applicable")),
                                ],
                            ),
                            MonitoringState(),
                        ],
                    ),
                    title=_("Map standby state"),
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="websphere_mq_manager",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Name of manager")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_websphere_mq_manager,
        title=lambda: _("Websphere MQ Manager"),
    )
)
