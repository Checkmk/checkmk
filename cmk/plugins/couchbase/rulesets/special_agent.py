#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    List,
    migrate_to_password,
    Password,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        migrate=_migrate,
        help_text=Help(
            "This rule allows to select a Couchbase server to monitor as well as "
            "configure buckets for further checks"
        ),
        elements={
            "buckets": DictElement(
                parameter_form=List(
                    title=Title("Bucket names"),
                    help_text=Help("Name of the Buckets to monitor."),
                    element_template=String(),
                ),
            ),
            "timeout": DictElement(
                parameter_form=Integer(
                    title=Title("Timeout"),
                    prefill=DefaultValue(10),
                    help_text=Help("Timeout for requests in seconds."),
                ),
            ),
            "port": DictElement(
                parameter_form=Integer(
                    title=Title("Port"),
                    prefill=DefaultValue(8091),
                    help_text=Help("The port that is used for the api call."),
                    custom_validate=(validators.NetworkPort(),),
                ),
            ),
            "authentication": DictElement(
                parameter_form=Dictionary(
                    title=Title("Authentication"),
                    help_text=Help("The credentials for api calls with authentication."),
                    elements={
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
                                title=Title("Password of the user"),
                                migrate=migrate_to_password,
                            ),
                        ),
                    },
                ),
            ),
        },
    )


rule_spec_special_agent_couchbase = SpecialAgent(
    name="couchbase",
    title=Title("Couchbase servers"),
    topic=Topic.DATABASES,
    parameter_form=_parameter_form,
)


def _migrate(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(value)
    if not isinstance(authentication := value.get("authentication"), tuple):
        return value
    return value | {
        "authentication": {
            "username": authentication[0],
            "password": authentication[1],
        }
    }
