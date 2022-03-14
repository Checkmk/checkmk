#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice, Percentage, TextInput, Tuple


def _parameter_valuespec_netscaler_vserver():
    return Dictionary(
        elements=[
            (
                "health_levels",
                Tuple(
                    title=_("Lower health levels"),
                    elements=[
                        Percentage(title=_("Warning below"), default_value=100.0),
                        Percentage(title=_("Critical below"), default_value=0.1),
                    ],
                ),
            ),
            (
                "cluster_status",
                DropdownChoice(
                    title=_("Cluster behaviour"),
                    help=_(
                        "Here you can choose the cluster behaviour. The best state "
                        "of all nodes is the default. This means, if  you have at "
                        "least one node in status UP the check returns OK. Health levels "
                        "should be the same on each node. If you choose worst, the check "
                        "will return CRIT if at least one node is in a state other than OK. "
                        "Health levels should be the same on each node, so only the first "
                        "node the health-levels are checked."
                    ),
                    choices=[
                        ("best", _("best state")),
                        ("worst", _("worst state")),
                    ],
                    default_value="best",
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="netscaler_vserver",
        group=RulespecGroupCheckParametersOperatingSystem,
        item_spec=lambda: TextInput(title=_("Name of VServer")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_netscaler_vserver,
        title=lambda: _("Netscaler VServer States"),
    )
)
