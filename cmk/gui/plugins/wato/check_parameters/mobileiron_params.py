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
from cmk.gui.valuespec import (
    Age,
    Checkbox,
    Dictionary,
    Integer,
    MonitoringState,
    Percentage,
    RegExp,
    Tuple,
)


def _parameter_valuespec_mobileiron_statistics() -> Dictionary:
    return Dictionary(
        title=_("Mobileiron statistics parameters"),
        elements=[
            (
                "non_compliant_summary_levels",
                Tuple(
                    title=_("Levels for non-compliant devices"),
                    elements=[
                        Percentage(title=_("Warning at"), default_value=10.0),
                        Percentage(title=_("Critical at"), default_value=20.0),
                    ],
                ),
            )
        ],
        optional_keys=[],
    )


def _parameter_valuespec_mobileiron_compliance() -> Dictionary:
    return Dictionary(
        title=_("Mobileiron compliance parameters"),
        elements=[
            (
                "policy_violation_levels",
                Tuple(
                    title=_("Configure policy violation levels"),
                    elements=[
                        Integer(title=_("Warning at"), default_value=2),
                        Integer(title=_("Critical at"), default_value=3),
                    ],
                ),
            ),
            (
                "ignore_compliance",
                Checkbox(
                    default_value=False,
                    title=_("Configure compliance state checking"),
                    label=_("Ignore compliance state"),
                ),
            ),
        ],
    )


def _parameter_valuespec_mobileiron_versions() -> Dictionary:
    return Dictionary(
        title=_("Mobileiron versions parameters"),
        elements=[
            (
                "ios_version_regexp",
                RegExp(
                    title=_("iOS version regular expression"),
                    mode=RegExp.infix,
                    help=_("iOS versions matching this pattern will be reported as OK, else CRIT."),
                ),
            ),
            (
                "android_version_regexp",
                RegExp(
                    title=_("Android version regular expression"),
                    mode=RegExp.infix,
                    help=_(
                        "Android versions matching this pattern will be reported as OK, else CRIT."
                    ),
                ),
            ),
            (
                "os_version_other",
                MonitoringState(
                    default_value=0,
                    title=_(
                        "State in case of the checked device is neither Android nor iOS (or cannot be read)"
                    ),
                ),
            ),
            (
                "patchlevel_unparsable",
                MonitoringState(default_value=0, title=_("State in case of unknown patch level")),
            ),
            (
                "patchlevel_age",
                Age(
                    title=_("Acceptable patch level age"),
                    display=["days"],
                    # three months
                    default_value=int(60 * 60 * 24 * 30 * 3),
                    minvalue=1,
                ),
            ),
            (
                "os_build_unparsable",
                MonitoringState(default_value=0, title=_("State in case of unknown OS build")),
            ),
            (
                "os_age",
                Age(
                    title=_("Acceptable OS build version age"),
                    display=["days"],
                    # three months
                    default_value=int(60 * 60 * 24 * 30 * 3),
                    minvalue=1,
                ),
            ),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        title=lambda: _("Mobileiron statistics"),
        check_group_name="mobileiron_statistics",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mobileiron_statistics,
    )
)

rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        title=lambda: _("Mobileiron compliance"),
        check_group_name="mobileiron_compliance",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mobileiron_compliance,
    )
)

rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        title=lambda: _("Mobileiron versions"),
        check_group_name="mobileiron_versions",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mobileiron_versions,
    )
)
