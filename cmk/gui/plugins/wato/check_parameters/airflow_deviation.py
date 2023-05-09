#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Float,
    TextAscii,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersEnvironment,
    CheckParameterRulespecWithItem,
    rulespec_registry,
)


def _item_spec_airflow_deviation():
    return TextAscii(
        title=_("Detector ID"),
        help=_("The identifier of the detector."),
    )


def _parameter_valuespec_airflow_deviation():
    return Tuple(
        help=_("Levels for Airflow Deviation measured at airflow sensors "),
        elements=[
            Float(title=_("critical if below or equal"), unit=u"%", default_value=-20),
            Float(title=_("warning if below or equal"), unit=u"%", default_value=-20),
            Float(title=_("warning if above or equal"), unit=u"%", default_value=20),
            Float(title=_("critical if above or equal"), unit=u"%", default_value=20),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="airflow_deviation",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_airflow_deviation,
        parameter_valuespec=_parameter_valuespec_airflow_deviation,
        title=lambda: _("Airflow Deviation in Percent"),
    ))
