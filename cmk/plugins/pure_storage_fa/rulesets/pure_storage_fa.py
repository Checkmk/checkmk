#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping

from cmk.rulesets.v1 import Localizable
from cmk.rulesets.v1.form_specs import (
    CascadingDropdown,
    CascadingDropdownElement,
    DictElement,
    Dictionary,
    FixedValue,
    Integer,
    Migrate,
    TextInput,
)
from cmk.rulesets.v1.preconfigured import Password
from cmk.rulesets.v1.rule_specs import EvalType, SpecialAgent, Topic
from cmk.rulesets.v1.validators import InRange


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
        title=Localizable("Pure Storage FlashArray"),
        elements={
            "api_token": DictElement(
                parameter_form=Password(
                    title=Localizable("API token"),
                    help_text=Localizable(
                        "Generate the API token through the Purity user interface"
                        " (System > Users > Create API Token)"
                        " or through the Purity command line interface"
                        " (pureadmin create --api-token)"
                    ),
                ),
                required=True,
            ),
            "ssl": DictElement(
                parameter_form=CascadingDropdown(
                    title=Localizable("SSL certificate checking"),
                    elements=[
                        CascadingDropdownElement(
                            name="deactivated",
                            title=Localizable("Deactivated"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingDropdownElement(
                            name="hostname",
                            title=Localizable("Use hostname"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingDropdownElement(
                            name="custom_hostname",
                            title=Localizable("Use other hostname"),
                            parameter_form=TextInput(
                                help_text=Localizable(
                                    "Use a custom name for the SSL certificate validation"
                                ),
                            ),
                        ),
                    ],
                    prefill_selection="hostname",
                ),
                required=True,
            ),
            "timeout": DictElement(
                parameter_form=Integer(
                    title=Localizable("Timeout"),
                    prefill_value=5,
                    custom_validate=InRange(min_value=1),
                ),
                required=True,
            ),
        },
        transform=Migrate(model_to_form=_migrate),
    )


rule_spec_pure_storage_fa = SpecialAgent(
    topic=Topic.STORAGE,
    name="pure_storage_fa",
    eval_type=EvalType.MERGE,
    title=Localizable("Pure Storage FlashArray"),
    parameter_form=_form_spec_special_agents_pure_storage_fa,
)
