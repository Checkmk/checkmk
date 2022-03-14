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
from cmk.gui.valuespec import Alternative, Dictionary, Integer, Percentage, TextInput, Tuple


def _item_spec_msoffice_licenses():
    return TextInput(title=_("MS Office 365 license"))


def _parameter_valuespec_msoffice_licenses():
    return Dictionary(
        elements=[
            (
                "usage",
                Alternative(
                    title=_("Upper levels for license usage"),
                    elements=[
                        Tuple(
                            title=_("Upper absolute levels"),
                            elements=[
                                Integer(title=_("Warning at")),
                                Integer(title=_("Critical at")),
                            ],
                        ),
                        Tuple(
                            title=_("Upper percentage levels"),
                            elements=[
                                Percentage(title=_("Warning at"), default_value=80.0),
                                Percentage(title=_("Critical at"), default_value=90.0),
                            ],
                        ),
                    ],
                ),
            ),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="msoffice_licenses",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_msoffice_licenses,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_msoffice_licenses,
        title=lambda: _("MS Office 365 licenses"),
    )
)


def _parameter_valuespec_msoffice_serviceplans():
    return Dictionary(
        elements=[
            (
                "levels",
                Tuple(
                    title=_("Upper levels for pending activations"),
                    elements=[
                        Integer(title=_("Warning at"), unit=_("services")),
                        Integer(title=_("Critical at"), unit=_("services")),
                    ],
                ),
            ),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="msoffice_serviceplans",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("MS Office 365 license")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_msoffice_serviceplans,
        title=lambda: _("MS Office 365 service plans"),
    )
)
