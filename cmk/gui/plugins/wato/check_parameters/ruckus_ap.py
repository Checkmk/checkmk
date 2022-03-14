#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Union

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import (
    Alternative,
    Dictionary,
    FixedValue,
    Integer,
    TextInput,
    Transform,
    Tuple,
)


def _item_spec_ruckus_ap():
    return TextInput(
        title=_("Band"),
        help=_("Name of the band, e.g. 5 GHz"),
    )


def _transform_forth(params: Union[tuple, dict]) -> dict:
    if isinstance(params, dict):
        return params
    drifted, not_responding = params
    return {
        "levels_drifted": None if drifted == (None, None) else drifted,
        "levels_not_responding": None if not_responding == (None, None) else not_responding,
    }


def _parameter_valuespec_ruckus_ap():
    return Transform(
        valuespec=Dictionary(
            elements=[
                (
                    "levels_drifted",
                    Alternative(
                        title=_("Upper levels for drifted access points"),
                        elements=[
                            FixedValue(
                                title=_("Do not impose levels"),
                                value=None,
                                totext="no levels (always OK)",
                            ),
                            Tuple(
                                elements=[
                                    Integer(
                                        title=_("Warning at"),
                                        default_value=1,
                                        unit=_("devices"),
                                    ),
                                    Integer(
                                        title=_("Critical at"),
                                        default_value=1,
                                        unit=_("devices"),
                                    ),
                                ],
                                title=_("Upper levels"),
                            ),
                        ],
                    ),
                ),
                (
                    "levels_not_responding",
                    Alternative(
                        title=_("Upper levels for unresponsive access points"),
                        elements=[
                            FixedValue(
                                title=_("Do not impose levels"),
                                value=None,
                                totext="no levels (always OK)",
                            ),
                            Tuple(
                                elements=[
                                    Integer(
                                        title=_("Warning at"),
                                        default_value=1,
                                        unit=_("devices"),
                                    ),
                                    Integer(
                                        title=_("Critical at"),
                                        default_value=1,
                                        unit=_("devices"),
                                    ),
                                ],
                                title=_("Upper levels"),
                            ),
                        ],
                    ),
                ),
            ]
        ),
        forth=_transform_forth,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ruckus_ap",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_ruckus_ap,
        parameter_valuespec=_parameter_valuespec_ruckus_ap,
        title=lambda: _("Ruckus Spot Access Points"),
    )
)
