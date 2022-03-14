#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    HostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersDiscovery,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Checkbox, Dictionary, DropdownChoice, Integer, TextInput, Transform


def _valuespec_inventory_heartbeat_crm_rules():
    return Dictionary(
        title=_("Heartbeat CRM discovery"),
        elements=[
            (
                "naildown_dc",
                Checkbox(
                    title=_("Naildown the DC"),
                    label=_("Mark the currently distinguished controller as preferred one"),
                    help=_(
                        "Nails down the DC to the node which is the DC during discovery. The check "
                        "will report CRITICAL when another node becomes the DC during later checks."
                    ),
                ),
            ),
            (
                "naildown_resources",
                Checkbox(
                    title=_("Naildown the resources"),
                    label=_("Mark the nodes of the resources as preferred one"),
                    help=_(
                        "Nails down the resources to the node which is holding them during discovery. "
                        "The check will report CRITICAL when another holds the resource during later checks."
                    ),
                ),
            ),
        ],
        help=_("This rule can be used to control the discovery for Heartbeat CRM checks."),
        optional_keys=[],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="dict",
        name="inventory_heartbeat_crm_rules",
        valuespec=_valuespec_inventory_heartbeat_crm_rules,
    )
)


def _heartbeat_crm_transform_heartbeat_crm(params):
    if isinstance(params, dict):
        _params = params.copy()
        _params.setdefault("show_failed_actions", False)
        return _params
    par_dict = {"max_age": params[0], "show_failed_actions": False}
    if params[1]:
        par_dict["dc"] = params[1]
    if params[2] > -1:
        par_dict["num_nodes"] = params[2]
    if params[3] > -1:
        par_dict["num_resources"] = params[3]
    return par_dict


def _parameter_valuespec_heartbeat_crm():
    return Transform(
        valuespec=Dictionary(
            elements=[
                (
                    "max_age",
                    Integer(
                        title=_("Maximum age"),
                        help=_("Maximum accepted age of the reported data in seconds"),
                        unit=_("seconds"),
                        default_value=60,
                    ),
                ),
                (
                    "dc",
                    TextInput(
                        allow_empty=False,
                        title=_("Expected DC"),
                        help=_(
                            "The hostname of the expected distinguished controller of the cluster"
                        ),
                    ),
                ),
                (
                    "num_nodes",
                    Integer(
                        minvalue=0,
                        default_value=2,
                        title=_("Number of Nodes"),
                        help=_("The expected number of nodes in the cluster"),
                    ),
                ),
                (
                    "num_resources",
                    Integer(
                        minvalue=0,
                        title=_("Number of Resources"),
                        help=_("The expected number of resources in the cluster"),
                    ),
                ),
                (
                    "show_failed_actions",
                    DropdownChoice(
                        title=_('Show "Failed Actions"'),
                        choices=[
                            (
                                False,
                                _('Don\'t show or warn if "Failed Actions" are present (default)'),
                            ),
                            (True, _('Show "Failed Actions" and warn if any is present')),
                        ],
                        default_value=False,
                        help=_(
                            'If activated, any "Failed Action" entry will be shown in the main check '
                            "and the check will go to the WARN state."
                        ),
                    ),
                ),
            ],
            optional_keys=["dc", "num_nodes", "num_resources", "show_failed_actions"],
        ),
        forth=_heartbeat_crm_transform_heartbeat_crm,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="heartbeat_crm",
        group=RulespecGroupCheckParametersStorage,
        parameter_valuespec=_parameter_valuespec_heartbeat_crm,
        title=lambda: _("Heartbeat CRM general status"),
    )
)
