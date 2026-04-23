#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    LevelDirection,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

THIRTY_DAYS = 30 * 24 * 60 * 60.0
SEVEN_DAYS = 7 * 24 * 60 * 60.0
SIX_MONTHS_ONE_DAY = 181 * 24 * 60 * 60.0


def _time_span() -> TimeSpan:
    return TimeSpan(
        displayed_magnitudes=[
            TimeMagnitude.DAY,
            TimeMagnitude.HOUR,
            TimeMagnitude.MINUTE,
            TimeMagnitude.SECOND,
        ]
    )


def _credential_validity_form(is_secret: bool) -> Dictionary:
    return Dictionary(
        title=Title("Check secret credentials")
        if is_secret
        else Title("Check certificate credentials"),
        elements={
            "remaining_validity": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Remaining validity time"),
                    form_spec_template=_time_span(),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=DefaultValue((THIRTY_DAYS, SEVEN_DAYS)),
                ),
            ),
            "max_validity": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Maximum allowed validity"),
                    form_spec_template=_time_span(),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((SIX_MONTHS_ONE_DAY, SIX_MONTHS_ONE_DAY)),
                ),
            ),
        },
    )


def _migrate(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError(value)

    # Already in new nested format
    if "secrets" in value or "certificates" in value:
        return value

    # Migrate from old flat format: expiration_time_secrets / expiration_time_certificates
    result: dict[str, object] = {}
    if "expiration_time_secrets" in value:
        result["secrets"] = {"remaining_validity": value["expiration_time_secrets"]}
    if "expiration_time_certificates" in value:
        result["certificates"] = {"remaining_validity": value["expiration_time_certificates"]}

    return result


def _make_form() -> Dictionary:
    return Dictionary(
        migrate=_migrate,
        elements={
            "secrets": DictElement(
                required=False,
                parameter_form=_credential_validity_form(is_secret=True),
            ),
            "certificates": DictElement(
                required=False,
                parameter_form=_credential_validity_form(is_secret=False),
            ),
        },
    )


rule_spec_azure_app_registration = CheckParameters(
    name="azure_v2_app_registration",
    topic=Topic.APPLICATIONS,
    parameter_form=_make_form,
    title=Title("Azure App Registration"),
    condition=HostAndItemCondition(item_title=Title("Credentials")),
)
