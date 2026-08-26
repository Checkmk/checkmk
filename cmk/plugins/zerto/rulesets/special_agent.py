#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Literal

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DictElement,
    Dictionary,
    FixedValue,
    migrate_to_password,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _form_spec_special_agents_zerto() -> Dictionary:
    return Dictionary(
        title=Title("Zerto"),
        help_text=Help(
            "Monitor if your VMs are properly protected by the "
            "disaster recovery software Zerto (compatible with Zerto v9.x)."
        ),
        elements={
            "authentication": DictElement(
                required=False,
                parameter_form=SingleChoice(
                    title=Title("Authentication method"),
                    elements=[
                        SingleChoiceElement(name="windows", title=Title("Windows authentication")),
                        SingleChoiceElement(name="vcenter", title=Title("VCenter authentication")),
                    ],
                    help_text=Help("Default is Windows authentication"),
                ),
            ),
            "username": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Username"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "password": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("Password"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                    migrate=migrate_to_password,
                ),
            ),
            "cert_verification": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("TLS certificate validation"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="secure",
                            title=Title("Verify the server certificate"),
                            parameter_form=Dictionary(
                                elements={
                                    "verify": DictElement(
                                        required=True,
                                        parameter_form=FixedValue(value=True),
                                    ),
                                    "cert_server_name": DictElement(
                                        required=False,
                                        parameter_form=String(
                                            title=Title("TLS certificate host name"),
                                            custom_validate=(
                                                validators.LengthInRange(min_value=1),
                                            ),
                                            help_text=Help(
                                                "The special agent will use this host "
                                                "name for the TLS certificate "
                                                "validation. If omitted, the Checkmk "
                                                "host name of the host will be used"
                                            ),
                                        ),
                                    ),
                                }
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="insecure",
                            title=Title("Do not verify the server certificate (unsafe)"),
                            parameter_form=Dictionary(
                                elements={
                                    "verify": DictElement(
                                        required=True,
                                        parameter_form=FixedValue(
                                            value=False,
                                        ),
                                    ),
                                },
                            ),
                        ),
                    ],
                ),
            ),
        },
        migrate=_migrate_to_cert_flag,
    )


def _migrate_to_cert_flag(
    value: object,
) -> dict[
    str,
    dict[
        str,
        Literal["windows", "vcenter"]
        | str
        | tuple[
            Literal["cmk_postprocessed"],
            Literal["explicit_password", "stored_password"],
            tuple[str, str],
        ]
        | tuple[Literal["secure", "insecure"], dict[str, bool | str]],
    ],
]:
    assert isinstance(value, dict)
    if value.get("cert_verification") is None:
        value["cert_verification"] = ("insecure", {"verify": False})

    return value


rule_spec_special_agent_zerto = SpecialAgent(
    name="zerto",
    title=Title("Zerto"),
    topic=Topic.APPLICATIONS,
    parameter_form=_form_spec_special_agents_zerto,
)
