#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    HostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersDiscovery,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Age, Checkbox, Dictionary, ListOf, TextInput, Tuple


def _parameter_valuespec_snapvault():
    return Dictionary(
        elements=[
            (
                "lag_time",
                Tuple(
                    title=_("Default levels"),
                    elements=[
                        Age(title=_("Warning at")),
                        Age(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "policy_lag_time",
                ListOf(
                    valuespec=Tuple(
                        orientation="horizontal",
                        elements=[
                            TextInput(title=_("Policy name")),
                            Tuple(
                                title=_("Maximum age"),
                                elements=[
                                    Age(title=_("Warning at")),
                                    Age(title=_("Critical at")),
                                ],
                            ),
                        ],
                    ),
                    title=_("Policy specific levels (Clustermode only)"),
                    help=_(
                        "Here you can specify levels for different policies which overrule the levels "
                        "from the <i>Default levels</i> parameter. This setting only works in NetApp Clustermode setups."
                    ),
                    allow_empty=False,
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="snapvault",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextInput(title=_("Source Path"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_snapvault,
        title=lambda: _("NetApp Snapvaults / Snapmirror Lag Time"),
    )
)


def _discovery_valuespec_snapvault():
    return Dictionary(
        elements=[
            (
                "exclude_destination_vserver",
                Checkbox(
                    title=_("Exclude destination vserver"),
                    help=_(
                        "Only applicable to clustermode installations. "
                        "The service description of snapvault services is composed of the "
                        "destination vserver (SVM) and the destination volume by default. Check "
                        "this box if you would like to use the destination volume as the "
                        "service description on its own. "
                        "Please be advised that this may lead to a service description that is "
                        "not unique, resulting in some services, which are not shown!"
                    ),
                ),
            ),
        ],
        title=_("NetApp snapvault discovery"),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="list",
        name="discovery_snapvault",
        valuespec=_discovery_valuespec_snapvault,
    )
)
