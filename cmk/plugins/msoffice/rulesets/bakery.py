#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def migrate(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "deployment" in value:
        return value
    match value:
        case None:
            return {"deployment": ("do_not_deploy", None)}
        case {"client_id": client_id, "tenant_id": tenant_id, "client_secret": client_secret}:
            return {
                "deployment": ("sync", None),
                "client_id": client_id,
                "tenant_id": tenant_id,
                "client_secret": migrate_to_password(client_secret),
            }
        case _:
            raise ValueError(f"Unexpected value: {value!r}")


def _form_spec() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This plug-in can be used to collect information of all MS Office 365 licenses and "
            "serviceplans using the MgGraph PowerShell module."
        ),
        migrate=migrate,
        elements={
            "deployment": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Deployment type"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="sync",
                            title=Title("Deploy the plug-in and run it synchronously"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="do_not_deploy",
                            title=Title("Do not deploy the plug-in"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ),
                    prefill=DefaultValue("sync"),
                ),
            ),
            "client_id": DictElement(
                parameter_form=String(
                    title=Title("ClientID"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "tenant_id": DictElement(
                parameter_form=String(
                    title=Title("TenantId"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "client_secret": DictElement(
                parameter_form=Password(
                    title=Title("ClientSecret"),
                    help_text=Help(
                        "Enter the client secret explicitly or select one from the password store."
                    ),
                ),
            ),
        },
    )


rule_spec_mk_msoffice = AgentConfig(
    title=Title("MS Office 365 (Windows)"),
    name="mk_msoffice",
    topic=Topic.APPLICATIONS,
    parameter_form=_form_spec,
)
