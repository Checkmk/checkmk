#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DictElement,
    Dictionary,
    FixedValue,
    Integer,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import ActiveCheck, Topic


def _migrate(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise TypeError(value)

    def _kept_values():
        return {str(k): v for k, v in value.items() if k != "job"}

    match value.get("job"):
        case None:
            return value
        case "version":
            return {"check_version": True, **_kept_values()}
        case ("address", address):
            return {"check_address": address, **_kept_values()}
        case other:
            raise ValueError(other)


def _valuespec_active_checks_uniserv():
    return Dictionary(
        migrate=_migrate,
        title=Title("Check uniserv service"),
        elements={
            "port": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Port"),
                    custom_validate=(validators.NetworkPort(),),
                ),
            ),
            "service": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Service Name"),
                    help_text=Help(
                        "Enter the uniserve service name here (has nothing to do with service name)."
                    ),
                ),
            ),
            "check_version": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("Create a service showing the version number"),
                ),
            ),
            "check_address": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Create a service checking the response to an address query"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="no",
                            title=Title("Do not check for an address"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="yes",
                            title=Title("Check for an address"),
                            parameter_form=Dictionary(
                                elements={
                                    "street": DictElement(
                                        required=True,
                                        parameter_form=String(title=Title("Street name")),
                                    ),
                                    "street_no": DictElement(
                                        required=True,
                                        parameter_form=Integer(title=Title("Street number")),
                                    ),
                                    "city": DictElement(
                                        required=True,
                                        parameter_form=String(title=Title("City name")),
                                    ),
                                    "search_regex": DictElement(
                                        required=True,
                                        parameter_form=String(
                                            title=Title("Check City against Regex"),
                                            help_text=Help(
                                                "The city name from the response will be checked against "
                                                "the regular expression specified here"
                                            ),
                                        ),
                                    ),
                                },
                            ),
                        ),
                    ],
                ),
            ),
        },
    )


rule_spec_active_check_uniserv = ActiveCheck(
    name="uniserv",
    title=Title("Check uniserv service"),
    topic=Topic.APPLICATIONS,
    parameter_form=_valuespec_active_checks_uniserv,
)
