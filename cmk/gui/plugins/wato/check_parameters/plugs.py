#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal, TypedDict, Union

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice, TextInput, Transform


def _item_spec_plugs() -> TextInput:
    return TextInput(
        title=_("Plug item number or name"),
        help=_(
            "Whether you need the number or the name depends on the check. Just take a look to the service description."
        ),
        allow_empty=True,
    )


CheckParamsValues = Literal["on", "off"]


class DiscoveredParams(TypedDict):
    discovered_state: str


class CheckParams(TypedDict, total=False):
    required_state: CheckParamsValues


def _transform(
    params: Union[int, CheckParamsValues, CheckParams, DiscoveredParams],
) -> Union[CheckParams, DiscoveredParams]:
    """
    An integer originates from earlier versions of the discovery functions of raritan_pdu_plugs and
    sentry_pdu. We cannot handle this case properly because the same integer has two different
    meanings in raritan_pdu_plugs and sentry_pdu.
    >>> _transform(1)
    {'discovered_state': 'unknown'}

    'On' and 'off' originate from this ruleset before it was transformed into a dictionary.
    >>> _transform("off")
    {'required_state': 'off'}
    >>> _transform("on")
    {'required_state': 'on'}

    A dictionary with the single, optional key 'required_state' originates from this ruleset.
    >>> _transform({"required_state": "off"})
    {'required_state': 'off'}
    >>> _transform({})
    {}

    A dictionary with the single key 'discovered_state' originates from the current versions of the
    discovery functions of raritan_pdu_plugs and sentry_pdu.
    >>> _transform({"discovered_state": "closed"})
    {'discovered_state': 'closed'}
    """
    if isinstance(params, int):
        return {"discovered_state": "unknown"}

    # using "params in ('off', 'on')" stops mypy from restricting the type of params to
    # CheckParamsValues within the if-condition
    if params == "off" or params == "on":  # pylint: disable=consider-using-in
        return {"required_state": params}

    assert isinstance(params, dict)
    return params


def _parameter_valuespec_plugs() -> Transform:
    return Transform(
        valuespec=Dictionary(
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
                        ],
                        default_value="on",
                    ),
                ),
            ],
        ),
        forth=_transform,
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
