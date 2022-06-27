#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Integer, TextInput, Tuple


def _item_spec_skype_proxy():
    return TextInput(
        title=_("Name of the Proxy"),
        help=_("The name of the Data Proxy"),
        allow_empty=False,
    )


def _parameter_valuespec_skype_proxy():
    return Dictionary(
        help=_("Warn/Crit levels for various Skype for Business (formerly known as Lync) metrics"),
        elements=[
            (
                "throttled_connections",
                Dictionary(
                    title=_("Throttled Server Connections"),
                    elements=[
                        (
                            "upper",
                            Tuple(
                                elements=[
                                    Integer(title=_("Warning at"), default_value=3),
                                    Integer(title=_("Critical at"), default_value=6),
                                ],
                            ),
                        ),
                    ],
                    optional_keys=[],
                ),
            ),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="skype_proxy",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_skype_proxy,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_skype_proxy,
        title=lambda: _("Skype for Business Data Proxy"),
    )
)
