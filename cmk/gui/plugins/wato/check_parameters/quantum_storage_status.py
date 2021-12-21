#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Dictionary, MonitoringState


def _parameter_valuespec_quantum_storage_status():
    return Dictionary(
        elements=[
            (
                "map_states",
                Dictionary(
                    elements=[
                        (
                            "unavailable",
                            MonitoringState(title=_("Device unavailable"), default_value=2),
                        ),
                        (
                            "available",
                            MonitoringState(title=_("Device available"), default_value=0),
                        ),
                        ("online", MonitoringState(title=_("Device online"), default_value=0)),
                        ("offline", MonitoringState(title=_("Device offline"), default_value=2)),
                        (
                            "going online",
                            MonitoringState(title=_("Device going online"), default_value=1),
                        ),
                        (
                            "state not available",
                            MonitoringState(title=_("Device state not available"), default_value=3),
                        ),
                    ],
                    title=_("Map Device States"),
                    optional_keys=[],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="quantum_storage_status",
        group=RulespecGroupCheckParametersStorage,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_quantum_storage_status,
        title=lambda: _("Quantum Storage Status"),
    )
)
