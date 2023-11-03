#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice, MonitoringState, TextInput, Tuple


def get_common_elements() -> list:
    return [
        (
            "expect_active",
            DropdownChoice(
                title=_("Warn on unexpected active interface"),
                choices=[
                    ("ignore", _("ignore which one is active")),
                    ("primary", _("require primary interface to be active")),
                    ("lowest", _("require interface that sorts lowest alphabetically")),
                ],
                default_value="ignore",
            ),
        ),
        (
            "ieee_302_3ad_agg_id_missmatch_state",
            MonitoringState(
                title=_("State for mismatching Aggregator IDs for LACP"),
                default_value=1,
            ),
        ),
    ]


def _parameter_valuespec_lnx_bonding():
    return Dictionary(
        elements=[
            *get_common_elements(),
            (
                "expected_bonding_mode_and_state",
                Tuple(
                    title=_("Expected bonding mode"),
                    elements=[
                        DropdownChoice(
                            title=_("Mode"),
                            choices=[
                                ("balance-rr", _("balance-rr")),
                                ("active-backup", _("active-backup")),
                                ("balance-xor", _("balance-xor")),
                                ("broadcast", _("broadcast")),
                                ("802.3ad", _("802.3ad")),
                                ("balance-tlb", _("balance-tlb")),
                                ("balance-alb", _("balance-alb")),
                            ],
                            default_value="balance-rr",
                        ),
                        MonitoringState(
                            title=_("State if not as expected"),
                            default_value=2,
                        ),
                    ],
                    help=_(
                        "Specify the monitoring state when the bonding mode is not as expected."
                    ),
                ),
            ),
        ],
        ignored_keys=["primary"],
    )


def _parameter_valuespec_ovs_bonding():
    return Dictionary(
        elements=get_common_elements(),
        ignored_keys=["primary"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="bonding",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextInput(title=_("Name of the bonding interface")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_lnx_bonding,
        title=lambda: _("Linux bonding interface status"),
    )
)

rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ovs_bonding",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextInput(title=_("Name of the bonding interface")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ovs_bonding,
        title=lambda: _("OVS bonding interface status"),
    )
)
