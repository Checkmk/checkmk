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
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice, Percentage, TextInput, Tuple


def _valuespec_ewon_discovery_rules():
    return DropdownChoice(
        title=_("eWON discovery"),
        help=_(
            "The ewon vpn routers can rely data from a secondary device via snmp. "
            "It doesn't however allow discovery of the device type relayed this way. "
            "To allow interpretation of the data you need to pick the device manually."
        ),
        label=_("Select device type"),
        choices=[
            (None, _("None selected")),
            ("oxyreduct", _("Wagner OxyReduct")),
        ],
        default_value=None,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        name="ewon_discovery_rules",
        valuespec=_valuespec_ewon_discovery_rules,
    )
)


def _item_spec_ewon():
    return TextInput(
        title=_("Item name"),
        help=_(
            "The item name. The meaning of this depends on the proxied device: "
            "- Wagner OxyReduct: Name of the room/protection zone"
        ),
    )


def _parameter_valuespec_ewon():
    return Dictionary(
        title=_("Device Type"),
        help=_(
            "The eWON router can act as a proxy to metrics from a secondary non-snmp device."
            "Here you can make settings to the monitoring of the proxied device."
        ),
        elements=[
            (
                "oxyreduct",
                Dictionary(
                    title=_("Wagner OxyReduct"),
                    elements=[
                        (
                            "o2_levels",
                            Tuple(
                                title=_("O2 levels"),
                                elements=[
                                    Percentage(title=_("Warning at"), default_value=16.0),
                                    Percentage(title=_("Critical at"), default_value=17.0),
                                    Percentage(title=_("Warning below"), default_value=14.0),
                                    Percentage(title=_("Critical below"), default_value=13.0),
                                ],
                            ),
                        )
                    ],
                ),
            )
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ewon",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_ewon,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ewon,
        title=lambda: _("eWON SNMP Proxy"),
    )
)
