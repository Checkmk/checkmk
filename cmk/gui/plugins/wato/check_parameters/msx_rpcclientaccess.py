#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Float, Integer, Transform, Tuple


def _ms_to_s(v: float) -> float:
    return v / 1000.0


def _s_to_ms(v: float) -> float:
    return v * 1000.0


def _migrate_milliseconds(values: object) -> dict:
    if not isinstance(values, dict):
        raise TypeError(values)

    if "latency_s" in values:
        return values

    values["latency_s"] = tuple(_ms_to_s(x) for x in values.pop("latency"))

    return values


def _parameter_valuespec_msx_rpcclientaccess():
    return Transform(
        forth=_migrate_milliseconds,
        back=lambda v: v,
        valuespec=Dictionary(
            title=_("Set levels"),
            elements=[
                (
                    "latency_s",
                    Tuple(
                        title=_("Average latency for RPC requests"),
                        elements=[
                            Transform(
                                valuespec=Float(
                                    title=_("Warning at"), unit=_("ms"), default_value=200.0
                                ),
                                back=_ms_to_s,
                                forth=_s_to_ms,
                            ),
                            Transform(
                                valuespec=Float(
                                    title=_("Critical at"), unit=_("ms"), default_value=250.0
                                ),
                                back=_ms_to_s,
                                forth=_s_to_ms,
                            ),
                        ],
                    ),
                ),
                (
                    "requests",
                    Tuple(
                        title=_("Maximum number of RPC requests per second"),
                        elements=[
                            Integer(title=_("Warning at"), unit=_("requests"), default_value=30),
                            Integer(title=_("Critical at"), unit=_("requests"), default_value=40),
                        ],
                    ),
                ),
            ],
            optional_keys=[],
        ),
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="msx_rpcclientaccess",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_msx_rpcclientaccess,
        title=lambda: _("MS Exchange RPC Client Access"),
    )
)
