#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
    TextInput,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Dictionary, Integer, Percentage


def _parameter_valuespec_byte_count():
    return Dictionary(
        title=_("Levels byte count"),
        elements=[
            (
                "upper_levels",
                SimpleLevels(Integer, title=_("Byte count upper levels"), unit="B/s"),
            ),
            (
                "lower_levels",
                SimpleLevels(Integer, title=_("Byte count lower levels"), unit="B/s"),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="byte_count",
        item_spec=lambda: TextInput(title=_("Byte Count")),
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_byte_count,
        title=lambda: _("Byte Count"),
    )
)

# TODO: migrate and move to new folder structure
rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="byte_count_without_item",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_byte_count,
        title=lambda: _("Byte Count"),
    )
)


def _parameter_valuespec_snat_usage():
    return Dictionary(
        title=_("Levels SNAT usage"),
        elements=[
            (
                "upper_levels",
                SimpleLevels(Percentage, title=_("SNAT usage upper levels")),
            ),
            (
                "lower_levels",
                SimpleLevels(Percentage, title=_("SNAT usage lower levels")),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="snat_usage",
        item_spec=lambda: TextInput(title=_("SNAT Consumption")),
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_snat_usage,
        title=lambda: _("SNAT Usage (Deprecated)"),
    )
)

# TODO: migrate and move to new folder structure
rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="snat_usage_without_item",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_snat_usage,
        title=lambda: _("SNAT Usage"),
    )
)
