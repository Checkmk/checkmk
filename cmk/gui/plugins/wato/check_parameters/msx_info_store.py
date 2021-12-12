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
from cmk.gui.valuespec import Dictionary, Float, Integer, TextInput, Tuple


def _item_spec_msx_info_store():
    return TextInput(
        title=_("Store"),
        help=_("Specify the name of a store (This is either a mailbox or public folder)"),
    )


def _parameter_valuespec_msx_info_store():
    return Dictionary(
        title=_("Set Levels"),
        elements=[
            (
                "store_latency",
                Tuple(
                    title=_("Average latency for store requests"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("ms"), default_value=40.0),
                        Float(title=_("Critical at"), unit=_("ms"), default_value=50.0),
                    ],
                ),
            ),
            (
                "clienttype_latency",
                Tuple(
                    title=_("Average latency for client type requests"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("ms"), default_value=40.0),
                        Float(title=_("Critical at"), unit=_("ms"), default_value=50.0),
                    ],
                ),
            ),
            (
                "clienttype_requests",
                Tuple(
                    title=_("Maximum number of client type requests per second"),
                    elements=[
                        Integer(title=_("Warning at"), unit=_("requests"), default_value=60),
                        Integer(title=_("Critical at"), unit=_("requests"), default_value=70),
                    ],
                ),
            ),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="msx_info_store",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_msx_info_store,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_msx_info_store,
        title=lambda: _("MS Exchange Information Store"),
    )
)
