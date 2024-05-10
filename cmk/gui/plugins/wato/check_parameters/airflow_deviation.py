#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import Dictionary, Float, Migrate, TextInput, Tuple


def _item_spec_airflow_deviation():
    return TextInput(
        title=_("Detector ID"),
        help=_("The identifier of the detector."),
    )


def _parameter_valuespec_airflow_deviation():
    return Migrate(
        valuespec=Dictionary(
            title=_("Airflow Deviation measured at airflow sensors"),
            elements=[
                (
                    "levels_upper",
                    Tuple(
                        title=_("Upper levels"),
                        elements=[
                            Float(title=_("warning at"), unit="%", default_value=20),
                            Float(title=_("critical at"), unit="%", default_value=20),
                        ],
                    ),
                ),
                (
                    "levels_lower",
                    Tuple(
                        help=_("Lower levels"),
                        elements=[
                            Float(
                                title=_("critical if below or equal"), unit="%", default_value=-20
                            ),
                            Float(
                                title=_("warning if below or equal"), unit="%", default_value=-20
                            ),
                        ],
                    ),
                ),
            ],
        ),
        migrate=lambda p: (
            p if isinstance(p, dict) else {"levels_upper": p[2:], "levels_lower": p[:2]}
        ),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="airflow_deviation",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_airflow_deviation,
        parameter_valuespec=_parameter_valuespec_airflow_deviation,
        title=lambda: _("Airflow Deviation in Percent"),
    )
)
