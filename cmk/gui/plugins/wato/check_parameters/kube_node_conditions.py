#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="type-arg"


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, ListOf, MonitoringState, TextInput, Tuple


def __elements() -> Tuple:
    return Tuple(
        elements=[
            TextInput(title="Type of node condition (case-insensitive)"),
            MonitoringState(
                title=_("Map `True` to"),
                default_value=2,
            ),
            MonitoringState(
                title=_("Map `False` to"),
                default_value=0,
            ),
            MonitoringState(
                title=_("Map `Unknown` to"),
                default_value=2,
            ),
        ],
    )


def _parameter_valuespec() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "conditions",
                ListOf(
                    valuespec=__elements(),
                    title=_("Add node condition"),
                    default_value=[
                        ("Ready", 0, 2, 2),
                        ("MemoryPressure", 2, 0, 2),
                        ("DiskPressure", 2, 0, 2),
                        ("PIDPressure", 2, 0, 2),
                        ("NetworkUnavailable", 2, 0, 2),
                    ],
                    add_label=_("Add new node condition"),
                ),
            ),
        ],
        required_keys="conditions",
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="kube_node_conditions",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec,
        title=lambda: _("Kubernetes node conditions"),
    )
)
