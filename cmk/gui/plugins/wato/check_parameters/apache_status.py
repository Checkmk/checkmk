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
from cmk.gui.valuespec import Dictionary, Integer, TextInput, Tuple


def _item_spec_apache_status():
    return TextInput(
        title=_("Apache Server"),
        help=_("A string-combination of servername and port, e.g. 127.0.0.1:5000."),
    )


def _parameter_valuespec_apache_status():
    return Dictionary(
        elements=[
            (
                "OpenSlots",
                Tuple(
                    title=_("Remaining Open Slots"),
                    help=_("Here you can set the number of remaining open slots"),
                    elements=[
                        Integer(title=_("Warning below"), label=_("slots")),
                        Integer(title=_("Critical below"), label=_("slots")),
                    ],
                ),
            ),
            (
                "BusyWorkers",
                Tuple(
                    title=_("Busy workers"),
                    help=_("Here you can set upper levels of busy workers"),
                    elements=[
                        Integer(title=_("Warning at"), label=_("busy workers")),
                        Integer(title=_("Critical at"), label=_("busy workers")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="apache_status",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_apache_status,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_apache_status,
        title=lambda: _("Apache Status"),
    )
)
