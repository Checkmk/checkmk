#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Age,
    Dictionary,
    Float,
    Integer,
    TextAscii,
    Transform,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersOperatingSystem,
    CheckParameterRulespecWithItem,
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
)


def _ntp_params():
    return Tuple(
        title=_("Thresholds for quality of time"),
        elements=[
            Integer(
                title=_("Critical at stratum"),
                default_value=10,
                help=
                _("The stratum (\"distance\" to the reference clock) at which the check gets critical."
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
        ])


def _item_spec_ntp_peer():
    return TextAscii(title=_("Name of the peer"))


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ntp_peer",
        group=RulespecGroupCheckParametersOperatingSystem,
        item_spec=_item_spec_ntp_peer,
        parameter_valuespec=_ntp_params,
        title=lambda: _("State of NTP peer"),
    ))


def _parameter_valuespec_ntp_time():
    return Transform(
        Dictionary(elements=[
            (
                "ntp_levels",
                _ntp_params(),
            ),
            ("alert_delay",
             Tuple(title=_("Phases without synchronization"),
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
                   ])),
        ],),
        forth=lambda params: isinstance(params, tuple) and {"ntp_levels": params} or params)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="ntp_time",
        group=RulespecGroupCheckParametersOperatingSystem,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ntp_time,
        title=lambda: _("State of NTP time synchronisation"),
    ))
