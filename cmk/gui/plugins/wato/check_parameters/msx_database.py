#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Float, TextInput, Transform, Tuple

_MS_KEY_MAP = {
    "read_attached_latency": "read_attached_latency_s",
    "read_recovery_latency": "read_recovery_latency_s",
    "write_latency": "write_latency_s",
    "log_latency": "log_latency_s",
}


def _ms_to_s(v: float) -> float:
    return v / 1000.0


def _s_to_ms(v: float) -> float:
    return v * 1000.0


Spec = Mapping[str, tuple[float, float]]


def _migrate_milliseconds(spec: Spec) -> Spec:
    if "read_attached_latency_s" in spec:
        return spec

    return {
        _MS_KEY_MAP.get(k, k): (_ms_to_s(v[0]), _ms_to_s(v[1])) if k in _MS_KEY_MAP else v
        for k, v in spec.items()
    }


def _item_spec_msx_database():
    return TextInput(
        title=_("Database Name"),
        help=_("Specify database names that the rule should apply to"),
    )


def _parameter_valuespec_msx_database():
    return Transform(
        forth=_migrate_milliseconds,
        back=lambda v: v,
        valuespec=Dictionary(
            title=_("Set Levels"),
            elements=[
                (
                    "read_attached_latency_s",
                    Tuple(
                        title=_("I/O Database Reads (Attached) Average Latency"),
                        elements=[
                            Transform(
                                valuespec=Float(
                                    title=_("Warning at"), unit="ms", default_value=200.0
                                ),
                                back=_ms_to_s,
                                forth=_s_to_ms,
                            ),
                            Transform(
                                valuespec=Float(
                                    title=_("Critical at"), unit="ms", default_value=250.0
                                ),
                                back=_ms_to_s,
                                forth=_s_to_ms,
                            ),
                        ],
                    ),
                ),
                (
                    "read_recovery_latency_s",
                    Tuple(
                        title=_("I/O Database Reads (Recovery) Average Latency"),
                        elements=[
                            Transform(
                                valuespec=Float(
                                    title=_("Warning at"), unit="ms", default_value=150.0
                                ),
                                back=_ms_to_s,
                                forth=_s_to_ms,
                            ),
                            Transform(
                                valuespec=Float(
                                    title=_("Critical at"), unit="ms", default_value=200.0
                                ),
                                back=_ms_to_s,
                                forth=_s_to_ms,
                            ),
                        ],
                    ),
                ),
                (
                    "write_latency_s",
                    Tuple(
                        title=_("I/O Database Writes (Attached) Average Latency"),
                        elements=[
                            Transform(
                                valuespec=Float(
                                    title=_("Warning at"), unit="ms", default_value=40.0
                                ),
                                back=_ms_to_s,
                                forth=_s_to_ms,
                            ),
                            Transform(
                                valuespec=Float(
                                    title=_("Critical at"), unit="ms", default_value=50.0
                                ),
                                back=_ms_to_s,
                                forth=_s_to_ms,
                            ),
                        ],
                    ),
                ),
                (
                    "log_latency_s",
                    Tuple(
                        title=_("I/O Log Writes Average Latency"),
                        elements=[
                            Transform(
                                valuespec=Float(
                                    title=_("Warning at"), unit="ms", default_value=5.0
                                ),
                                back=_ms_to_s,
                                forth=_s_to_ms,
                            ),
                            Transform(
                                valuespec=Float(
                                    title=_("Critical at"), unit="ms", default_value=10.0
                                ),
                                back=_ms_to_s,
                                forth=_s_to_ms,
                            ),
                        ],
                    ),
                ),
            ],
            optional_keys=[],
        ),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="msx_database",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_msx_database,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_msx_database,
        title=lambda: _("MS Exchange Database"),
    )
)
