#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import Alternative, Dictionary, FixedValue, MonitoringState, TextInput

# Duplicated code from checkplugin... one bright day we may import from there?
STATE_EVAL_KEY = "evaluation_mode"
AS_DISCOVERED = "as_discovered"
STATES_DURING_DISC_KEY = "states_during_discovery"


def _item_spec_wut_webio():
    return TextInput(
        title=_("Input channel"),
        help=_("Name of the input channel, e.g. WEBIO-094849 Input 0"),
    )


def _valuespec_wut_webio_check():
    return Dictionary(
        title=_("W&T WebIO"),
        ignored_keys=[STATE_EVAL_KEY, STATES_DURING_DISC_KEY],
        elements=[
            (
                STATE_EVAL_KEY,
                Alternative(
                    title=_("Specify input state evaluation"),
                    elements=[
                        FixedValue(
                            title=_("Consider the input states during discovery to be OK"),
                            help=_(
                                "If this option is activated, the state of an input "
                                "during the discovery will be evaluated as OK. All "
                                "other states will result in CRIT."
                            ),
                            totext="",
                            value=AS_DISCOVERED,
                        ),
                        Dictionary(
                            title=_("Custom input state mapping"),
                            help=_(
                                "Define which monitoring state maps "
                                "which input state. This applies for every "
                                "single input."
                            ),
                            default_keys=["Off", "On"],
                            required_keys=["Off", "On"],
                            elements=[
                                (
                                    "Off",
                                    MonitoringState(
                                        title=_("State if input is OFF"),
                                        default_value=2,
                                    ),
                                ),
                                (
                                    "On",
                                    MonitoringState(
                                        title=_("State if input is ON"), default_value=0
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="wut_webio",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_wut_webio,
        parameter_valuespec=_valuespec_wut_webio_check,
    )
)
