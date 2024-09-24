#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    Migrate,
    MonitoringState,
    TextInput,
    Tuple,
    ValueSpec,
)


def _item_spec() -> ValueSpec:
    return TextInput(
        title=_("Contact sensor type"),
        help=_(
            "The item of etherbox checks is build as 'contact.sensor_type'. "
            "For example, you want the rule to only apply to a temperature sensor (type 1) on contact 3 "
            "then set the item to 3.1 ."
        ),
    )


def _vs_voltage() -> ValueSpec:
    return Migrate(
        Dictionary(
            title=_("Voltage levels"),
            elements=[
                (
                    "levels",
                    SimpleLevels(
                        title=_("Voltage Levels"),
                        unit="V",
                    ),
                )
            ],
            optional_keys=[],
        ),
        migrate=lambda p: {"levels": None} if isinstance(p["levels"], dict) else p,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="etherbox_voltage",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_vs_voltage,
        title=lambda: _("Etherbox voltage"),
        item_spec=_item_spec,
    )
)


def _vs_smoke() -> ValueSpec:
    return Migrate(
        Dictionary(
            title=_("Smoke monitoring"),
            elements=[
                (
                    "smoke_handling",
                    CascadingDropdown(
                        title=_("Smoke handling"),
                        choices=[
                            (
                                "binary",
                                _("Set monitoring states for no-smoke and smoke cases"),
                                Tuple(
                                    elements=[
                                        MonitoringState(
                                            title=_("Monitoring state if no smoke is detected"),
                                        ),
                                        MonitoringState(
                                            title=_("Monitoring state if smoke is detected"),
                                        ),
                                    ],
                                ),
                            ),
                            (
                                "levels",
                                _("Configure levels on smoke"),
                                SimpleLevels(title=_("Smoke Levels")),
                            ),
                        ],
                        sorted=False,
                    ),
                )
            ],
            optional_keys=[],
        ),
        migrate=_migrate_smoke,
    )


def _migrate_smoke(
    p: dict[Literal["levels"] | Literal["smoke_handling"], object],
) -> dict[Literal["smoke_handling"], object]:
    if "smoke_handling" in p:
        return {"smoke_handling": p["smoke_handling"]}
    match p["levels"]:
        case None:
            return {"smoke_handling": ("levels", None)}
        case (warn, crit):
            return {"smoke_handling": ("levels", (warn, crit))}
        case _:
            return {"smoke_handling": ("binary", (0, 2))}


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="etherbox_smoke",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_vs_smoke,
        title=lambda: _("Etherbox smoke"),
        item_spec=_item_spec,
    )
)
