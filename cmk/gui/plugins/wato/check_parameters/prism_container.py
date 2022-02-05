#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Alternative, Dictionary, Filesize, Percentage, TextInput, Tuple


def _item_spec_prism_container():
    return TextInput(
        title=_("Container Name"),
        help=_("Name of the container"),
    )


def _parameter_valuespec_prism_container():
    return Dictionary(
        elements=[
            (
                "levels",
                Alternative(
                    title=_("Usage levels"),
                    default_value=(80.0, 90.0),
                    elements=[
                        Tuple(
                            title=_("Specify levels in percentage of total space"),
                            elements=[
                                Percentage(title=_("Warning at"), unit=_("%")),
                                Percentage(title=_("Critical at"), unit=_("%")),
                            ],
                        ),
                        Tuple(
                            title=_("Specify levels in absolute usage"),
                            elements=[
                                Filesize(title=_("Warning at"), default_value=1000 * 1024 * 1024),
                                Filesize(title=_("Critical at"), default_value=5000 * 1024 * 1024),
                            ],
                        ),
                    ],
                ),
            )
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="prism_container",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_prism_container,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_prism_container,
        title=lambda: _("Nutanix Prism"),
    )
)
