#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    TextAscii,
    Transform,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)


def _item_spec_plugs():
    return TextAscii(
        title=_("Plug item number or name"),
        help=
        _("Whether you need the number or the name depends on the check. Just take a look to the service description."
         ),
        allow_empty=True)


def _transform(params):
    if isinstance(params, dict):
        return params
    if params in ('on', 'off'):
        return {'required_state': params}
    return {}


def _parameter_valuespec_plugs():
    return Transform(
        Dictionary(
            ignored_keys=['discoverd_state'],
            elements=[
                ('required_state',
                 DropdownChoice(
                     help=_("This rule sets the required state of a PDU plug. It is meant to "
                            "be independent of the hardware manufacturer."),
                     title=_("Required plug state"),
                     choices=[
                         ("on", _("Plug is ON")),
                         ("off", _("Plug is OFF")),
                     ],
                     default_value="on",
                 )),
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
    ))
