#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersDiscovery,
)
from cmk.gui.valuespec import (
    Alternative,
    Dictionary,
    FixedValue,
    Integer,
    ListOf,
    RegExp,
    TextInput,
    Transform,
    Tuple,
)


def _valuespec_inventory_sap_values():
    return Dictionary(
        title=_("SAP R/3 single value discovery"),
        elements=[
            (
                "match",
                Alternative(
                    title=_("Node Path Matching"),
                    elements=[
                        TextInput(
                            title=_("Exact path of the node"),
                            size=100,
                        ),
                        Transform(
                            valuespec=RegExp(
                                size=100,
                                mode=RegExp.prefix,
                            ),
                            title=_("Regular expression matching the path"),
                            help=_(
                                "This regex must match the <i>beginning</i> of the complete "
                                "path of the node as reported by the agent"
                            ),
                            forth=lambda x: x[1:],  # remove ~
                            back=lambda x: "~" + x,  # prefix ~
                        ),
                        FixedValue(
                            value=None,
                            totext="",
                            title=_("Match all nodes"),
                        ),
                    ],
                    match=lambda x: (not x and 2) or (x[0] == "~" and 1 or 0),
                    default_value="SAP CCMS Monitor Templates/Dialog Overview/Dialog Response Time/ResponseTime",
                ),
            ),
            (
                "limit_item_levels",
                Integer(
                    title=_("Limit Path Levels for Service Names"),
                    unit=_("path levels"),
                    minvalue=1,
                    help=_(
                        "The service descriptions of the inventorized services are named like the paths "
                        "in SAP. You can use this option to let the inventory function only use the last "
                        "x path levels for naming."
                    ),
                ),
            ),
        ],
        optional_keys=["limit_item_levels"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="all",
        name="inventory_sap_values",
        valuespec=_valuespec_inventory_sap_values,
    )
)


def _valuespec_sap_value_groups():
    return Transform(
        valuespec=Dictionary(
            title=_("SAP R/3 grouped values discovery"),
            elements=[
                (
                    "grouping_patterns",
                    ListOf(
                        valuespec=Tuple(
                            help=_("This defines one value grouping pattern"),
                            show_titles=True,
                            orientation="horizontal",
                            elements=[
                                TextInput(
                                    title=_("Name of group"),
                                ),
                                Tuple(
                                    show_titles=True,
                                    orientation="vertical",
                                    elements=[
                                        RegExp(
                                            title=_("Include Pattern"),
                                            mode=RegExp.prefix,
                                        ),
                                        RegExp(
                                            title=_("Exclude Pattern"),
                                            mode=RegExp.prefix,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        add_label=_("Add pattern group"),
                    ),
                )
            ],
            optional_keys=[],
            help=_(
                "The check <tt>sap.value</tt> normally creates one service for each SAP value. "
                "By defining grouping patterns, you can switch to the check <tt>sap.value_groups</tt>. "
                "That check monitors a list of SAP values at once."
            ),
        ),
        forth=lambda p: p if isinstance(p, dict) else {"grouping_patterns": p},
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="all",
        name="sap_value_groups",
        valuespec=_valuespec_sap_value_groups,
    )
)
