#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    CheckParameterRulespecWithoutItem,
    HostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersDiscovery,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import (
    Age,
    Dictionary,
    DropdownChoice,
    Float,
    Integer,
    TextInput,
    Transform,
    Tuple,
)


def _valuespec_ntp_rules():
    return Transform(
        valuespec=Dictionary(
            title=_("NTP discovery"),
            elements=[
                (
                    "mode",
                    DropdownChoice(
                        choices=[
                            ("summary", "Discover a single summary service"),
                            ("single", "Discover one service for every peer"),
                            ("both", "Discover both of the above"),
                            ("neither", "Discover neither of the above"),
                        ],
                        title=_("Single peers or summary"),
                    ),
                )
            ],
        )
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="merged",
        name="ntp_discovery",
        valuespec=_valuespec_ntp_rules,
    )
)


def _ntp_params():
    return Tuple(
        title=_("Thresholds for quality of time"),
        elements=[
            Integer(
                title=_("Critical at stratum"),
                default_value=10,
                help=_(
                    'The stratum ("distance" to the reference clock) at which the check gets critical.'
                ),
            ),
            Float(
                title=_("Warning at"),
                unit=_("ms"),
                default_value=200.0,
                help=_("The offset in ms at which a warning state is triggered."),
            ),
            Float(
                title=_("Critical at"),
                unit=_("ms"),
                default_value=500.0,
                help=_("The offset in ms at which a critical state is triggered."),
            ),
        ],
    )


def _parameter_valuespec_ntp_peer():
    return Transform(
        valuespec=Dictionary(
            elements=[
                ("ntp_levels", _ntp_params()),
            ],
            ignored_keys=["alert_delay"],  # be compatible to ntp_time defaults
        ),
        forth=_transform_forth,
    )


def _item_spec_ntp_peer():
    return TextInput(title=_("Name of the peer"))


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ntp_peer",
        group=RulespecGroupCheckParametersOperatingSystem,
        item_spec=_item_spec_ntp_peer,
        parameter_valuespec=_parameter_valuespec_ntp_peer,
        title=lambda: _("State of NTP peer"),
    )
)


def _parameter_valuespec_ntp_time():
    return Transform(
        valuespec=Dictionary(
            elements=[
                (
                    "ntp_levels",
                    _ntp_params(),
                ),
                (
                    "alert_delay",
                    Tuple(
                        title=_("Phases without synchronization"),
                        elements=[
                            Age(
                                title=_("Warning at"),
                                display=["hours", "minutes"],
                                default_value=300,
                            ),
                            Age(
                                title=_("Critical at"),
                                display=["hours", "minutes"],
                                default_value=3600,
                            ),
                        ],
                    ),
                ),
            ],
        ),
        forth=_transform_forth,
    )


def _transform_forth(params):
    if isinstance(params, dict):
        return params
    return {"ntp_levels": params}


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="ntp_time",
        group=RulespecGroupCheckParametersOperatingSystem,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ntp_time,
        title=lambda: _("State of NTP time synchronisation"),
    )
)
