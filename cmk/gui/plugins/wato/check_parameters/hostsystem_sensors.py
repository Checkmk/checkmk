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


def _parameter_valuespec_hostsystem_sensors():
    return ListOf(
        valuespec=Dictionary(
            help=_("This rule allows to override alert levels for the given sensor names."),
            elements=[
                ("name", TextInput(title=_("Sensor name"))),
                (
                    "states",
                    Dictionary(
                        title=_("Custom states"),
                        elements=[
                            (
                                element,
                                MonitoringState(
                                    title="Sensor %s" % description,
                                    label=_("Set state to"),
                                    default_value=int(element),
                                ),
                            )
                            for (element, description) in [
                                ("0", _("OK")),
                                ("1", _("WARNING")),
                                ("2", _("CRITICAL")),
                                ("3", _("UNKNOWN")),
                            ]
                        ],
                    ),
                ),
            ],
            optional_keys=False,
        ),
        add_label=_("Add sensor name"),
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="hostsystem_sensors",
        group=RulespecGroupCheckParametersEnvironment,
        parameter_valuespec=_parameter_valuespec_hostsystem_sensors,
        title=lambda: _("Hostsystem sensor alerts"),
    )
)
