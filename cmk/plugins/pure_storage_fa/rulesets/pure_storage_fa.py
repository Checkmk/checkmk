#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    migrate_to_password,
    Password,
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _migrate(value: object) -> Mapping[str, int | tuple[str | None] | tuple[str, str]]:
    if not isinstance(value, dict):
        raise TypeError(value)

    migrated = value.copy()
    if "timeout" not in value:
        migrated["timeout"] = 5

    if isinstance(value["ssl"], tuple):
        return migrated

    ssl_config = value.pop("ssl")
    if isinstance(ssl_config, bool):
        migrated["ssl"] = ("hostname" if ssl_config else "deactivated", None)
    else:
        migrated["ssl"] = ("custom_hostname", ssl_config)

    return migrated


def _form_spec_special_agents_pure_storage_fa() -> Dictionary:
    return Dictionary(
        title=Title("Pure Storage FlashArray"),
        elements={
            "api_token": DictElement(
                parameter_form=Password(
                    title=Title("API token"),
                    help_text=Help(
                        "Generate the API token through the Purity user interface"
                        " (System > Users > Create API Token)"
                        " or through the Purity command line interface"
                        " (pureadmin create --api-token)"
                    ),
                    migrate=migrate_to_password,
                ),
                required=True,
            ),
            "ssl": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("SSL certificate checking"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="deactivated",
                            title=Title("Deactivated"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="hostname",
                            title=Title("Use host name"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="custom_hostname",
                            title=Title("Use other host name"),
                            parameter_form=String(
                                help_text=Help(
                                    "Use a custom name for the SSL certificate validation"
                                ),
                                macro_support=True,
                            ),
                        ),
                    ],
                    prefill=DefaultValue("hostname"),
                ),
                required=True,
            ),
            "timeout": DictElement(
                parameter_form=TimeSpan(
                    title=Title("Timeout"),
                    displayed_magnitudes=[
                        TimeMagnitude.SECOND,
                    ],
                    custom_validate=(validators.NumberInRange(min_value=1),),
                    prefill=DefaultValue(5.0),
                ),
                required=True,
            ),
        },
        migrate=_migrate,
    )


rule_spec_pure_storage_fa = SpecialAgent(
    topic=Topic.STORAGE,
    name="pure_storage_fa",
    title=Title("Pure Storage FlashArray"),
    parameter_form=_form_spec_special_agents_pure_storage_fa,
)
