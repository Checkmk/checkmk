#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, ListOf, Migrate, MonitoringState, TextInput, Tuple


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


def _parameter_valuespec():
    return Migrate(
        Dictionary(
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
        ),
        migrate=migrate,
    )


def migrate(
    value: dict[str, int] | dict[str, list[tuple[str, int, int, int]]],
) -> dict[str, list[tuple[str, int, int, int]]]:
    if "conditions" in value:
        return value  # type: ignore[return-value]
    old: dict[str, int] = value  # type: ignore[assignment]

    def by_key(key: str, value: int) -> tuple[str, int, int, int]:
        match key:
            case "ready":
                return ("Ready", 0, value, 2)
            case "memorypressure":
                return ("MemoryPressure", value, 0, 2)
            case "diskpressure":
                return ("DiskPressure", value, 0, 2)
            case "pidpressure":
                return ("PIDPressure", value, 0, 2)
            case "networkunavailable":
                return ("NetworkUnavailable", value, 0, 2)
        assert False, f"Unknown key {key}, value: {value}"

    conditions = [by_key(key, value) for key, value in old.items()]
    if all(key != "Ready" for (key, _, _, _) in conditions):
        conditions.append(("Ready", 0, 2, 2))
    return {"conditions": conditions}


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="kube_node_conditions",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec,
        title=lambda: _("Kubernetes node conditions"),
    )
)
