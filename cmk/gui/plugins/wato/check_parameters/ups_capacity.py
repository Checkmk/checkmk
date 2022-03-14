#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import Dictionary, Integer, Tuple


def _parameter_valuespec_ups_capacity():
    return Dictionary(
        title=_("Levels for battery parameters"),
        optional_keys=["battime"],
        elements=[
            (
                "capacity",
                Tuple(
                    title=_("Battery capacity"),
                    elements=[
                        Integer(
                            title=_("Warning at"),
                            help=_(
                                "The battery capacity in percent at and below which a warning state is triggered"
                            ),
                            unit="%",
                            default_value=95,
                        ),
                        Integer(
                            title=_("Critical at"),
                            help=_(
                                "The battery capacity in percent at and below which a critical state is triggered"
                            ),
                            unit="%",
                            default_value=90,
                        ),
                    ],
                ),
            ),
            (
                "battime",
                Tuple(
                    title=_("Time left on battery"),
                    elements=[
                        Integer(
                            title=_("Warning at"),
                            help=_(
                                "Time left on Battery at and below which a warning state is triggered"
                            ),
                            unit=_("min"),
                            default_value=0,
                        ),
                        Integer(
                            title=_("Critical at"),
                            help=_(
                                "Time Left on Battery at and below which a critical state is triggered"
                            ),
                            unit=_("min"),
                            default_value=0,
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="ups_capacity",
        group=RulespecGroupCheckParametersEnvironment,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ups_capacity,
        title=lambda: _("UPS Capacity"),
    )
)
