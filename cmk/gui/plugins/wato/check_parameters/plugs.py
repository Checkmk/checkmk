#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal, TypedDict

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice, TextInput


def _item_spec_plugs() -> TextInput:
    return TextInput(
        title=_("Plug item number or name"),
        help=_(
            "Whether you need the number or the name depends on the check. Just take a look to the service name."
        ),
        allow_empty=True,
    )


CheckParamsValues = Literal["on", "off"]


class DiscoveredParams(TypedDict):
    discovered_state: str


class CheckParams(TypedDict, total=False):
    required_state: CheckParamsValues


def _parameter_valuespec_plugs() -> Dictionary:
    return Dictionary(
        ignored_keys=["discovered_state"],
        elements=[
            (
                "required_state",
                DropdownChoice(
                    help=_(
                        "This rule sets the required state of a PDU plug. It is meant to "
                        "be independent of the hardware manufacturer."
                    ),
                    title=_("Required plug state"),
                    choices=[
                        ("on", _("Plug is ON")),
                        ("off", _("Plug is OFF")),
                        (None, _("State found during service discovery")),
                    ],
                    default_value="on",
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="plugs",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_plugs,
        parameter_valuespec=_parameter_valuespec_plugs,
        title=lambda: _("PDU Plug state"),
    )
)
