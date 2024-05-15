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
from cmk.gui.valuespec import Dictionary, DropdownChoice, MonitoringState, TextInput


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
                "bonding_mode_states",
                Dictionary(
                    title=_("State for specific bonding modes"),
                    optional_keys=[],
                    elements=[
                        ("mode_0", MonitoringState(title=_("balance-rr"), default_value=0)),
                        ("mode_1", MonitoringState(title=_("active-backup"), default_value=0)),
                        ("mode_2", MonitoringState(title=_("balance-xor"), default_value=0)),
                        ("mode_3", MonitoringState(title=_("broadcast"), default_value=0)),
                        ("mode_4", MonitoringState(title=_("802.3ad"), default_value=0)),
                        ("mode_5", MonitoringState(title=_("balance-tlb"), default_value=0)),
                        ("mode_6", MonitoringState(title=_("balance-alb"), default_value=0)),
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
