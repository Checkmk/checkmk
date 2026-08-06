#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    MatchingScope,
    RegularExpression,
    ServiceState,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic

_THREE_MONTHS = float(60 * 60 * 24 * 30 * 3)


def _acceptable_age(title: Title) -> DictElement[float]:
    return DictElement(
        required=True,
        parameter_form=TimeSpan(
            title=title,
            displayed_magnitudes=(TimeMagnitude.DAY,),
            prefill=DefaultValue(_THREE_MONTHS),
        ),
    )


def _version_regexp(title: Title, help_text: Help) -> DictElement[str]:
    return DictElement(
        required=True,
        parameter_form=RegularExpression(
            title=title,
            help_text=help_text,
            predefined_help_text=MatchingScope.INFIX,
            prefill=DefaultValue(""),
        ),
    )


def _parameter_form_mobileiron_versions() -> Dictionary:
    return Dictionary(
        elements={
            "ios_version_regexp": _version_regexp(
                Title("iOS version regular expression"),
                Help("iOS versions matching this pattern will be reported as OK, else CRIT."),
            ),
            "android_version_regexp": _version_regexp(
                Title("Android version regular expression"),
                Help("Android versions matching this pattern will be reported as OK, else CRIT."),
            ),
            "os_version_other": DictElement(
                required=True,
                parameter_form=ServiceState(
                    title=Title(
                        "State in case the checked device is neither Android nor iOS "
                        "(or cannot be read)"
                    ),
                    prefill=DefaultValue(0),
                ),
            ),
            "patchlevel_unparsable": DictElement(
                required=True,
                parameter_form=ServiceState(
                    title=Title("State in case of unknown patch level"),
                    prefill=DefaultValue(0),
                ),
            ),
            "patchlevel_age": _acceptable_age(Title("Acceptable patch level age")),
            "os_build_unparsable": DictElement(
                required=True,
                parameter_form=ServiceState(
                    title=Title("State in case of unknown OS build"),
                    prefill=DefaultValue(0),
                ),
            ),
            "os_age": _acceptable_age(Title("Acceptable OS build version age")),
        },
    )


rule_spec_mobileiron_versions = CheckParameters(
    name="mobileiron_versions",
    # weblate-flags: read-only, vendor-name
    title=Title("MobileIron versions"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_mobileiron_versions,
    condition=HostCondition(),
)
