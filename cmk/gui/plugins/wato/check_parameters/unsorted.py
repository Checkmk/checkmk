#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.active_checks import check_icmp_params
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersDiscovery,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import (
    Alternative,
    Dictionary,
    DualListChoice,
    FixedValue,
    Integer,
    ListOf,
    ListOfStrings,
    RegExp,
    TextInput,
    Transform,
    Tuple,
)

# TODO: Sort all rules and check parameters into the figlet header sections.
# Beware: there are dependencies, so sometimes the order matters.  All rules
# that are not yet handles are in the last section: in "Unsorted".  Move rules
# from there into their appropriate sections until "Unsorted" is empty.
# Create new rules directly in the correct secions.

#   .--Networking----------------------------------------------------------.
#   |        _   _      _                      _    _                      |
#   |       | \ | | ___| |___      _____  _ __| | _(_)_ __   __ _          |
#   |       |  \| |/ _ \ __\ \ /\ / / _ \| '__| |/ / | '_ \ / _` |         |
#   |       | |\  |  __/ |_ \ V  V / (_) | |  |   <| | | | | (_| |         |
#   |       |_| \_|\___|\__| \_/\_/ \___/|_|  |_|\_\_|_| |_|\__, |         |
#   |                                                       |___/          |
#   '----------------------------------------------------------------------'


def _valuespec_ping_levels():
    return Dictionary(
        title=_("PING and host check parameters"),
        help=_(
            "This rule sets the parameters for the host checks (via <tt>check_icmp</tt>) "
            "and also for PING checks on ping-only-hosts. For the host checks only the "
            "critical state is relevant, the warning levels are ignored."
        ),
        elements=check_icmp_params(),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersNetworking,
        match_type="dict",
        name="ping_levels",
        valuespec=_valuespec_ping_levels,
    )
)

# .
#   .--Inventory-----------------------------------------------------------.
#   |            ___                      _                                |
#   |           |_ _|_ ____   _____ _ __ | |_ ___  _ __ _   _              |
#   |            | || '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |             |
#   |            | || | | \ V /  __/ | | | || (_) | |  | |_| |             |
#   |           |___|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |             |
#   |                                                   |___/              |
#   '----------------------------------------------------------------------'


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
                            RegExp(
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
    return ListOf(
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
        title=_("SAP value discovery"),
        help=_(
            "The check <tt>sap.value</tt> normally creates one service for each SAP value. "
            "By defining grouping patterns, you can switch to the check <tt>sap.value_groups</tt>. "
            "That check monitors a list of SAP values at once."
        ),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="all",
        name="sap_value_groups",
        valuespec=_valuespec_sap_value_groups,
    )
)


def _valuespec_inventory_fujitsu_ca_ports():
    return Dictionary(
        title=_("Fujtsu storage CA port discovery"),
        elements=[
            ("indices", ListOfStrings(title=_("CA port indices"))),
            (
                "modes",
                DualListChoice(
                    title=_("CA port modes"),
                    choices=[
                        ("CA", _("CA")),
                        ("RA", _("RA")),
                        ("CARA", _("CARA")),
                        ("Initiator", _("Initiator")),
                    ],
                    rows=4,
                    size=30,
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="dict",
        name="inventory_fujitsu_ca_ports",
        valuespec=_valuespec_inventory_fujitsu_ca_ports,
    )
)
