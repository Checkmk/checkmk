#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    Levels,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, TextInput, ValueSpec


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
    return Dictionary(
        title=_("Voltage levels"),
        elements=[("levels", Levels(title=_("Voltage Levels")))],
        required_keys=["levels"],
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
    return Dictionary(
        title=_("Smoke levels"),
        elements=[("levels", Levels(title=_("Smoke Levels")))],
        required_keys=["levels"],
    )


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
