#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    migrate_to_password,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.form_specs.validators import NetworkPort
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _formspec_bazel_cache() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "Requests data from a Bazel Remote Cache instance metrics endpoint running version v2.4.1 or higher"
        ),
        elements={
            "user": DictElement(
                parameter_form=String(
                    title=Title("Bazel Cache User"),
                    help_text=Help("The username used to connect to the Bazel cache"),
                ),
                required=False,
            ),
            "password": DictElement(
                parameter_form=Password(
                    title=Title("Bazel Cache password"),
                    help_text=Help("The password used to connect to the Bazel cache"),
                    migrate=migrate_to_password,
                ),
                required=False,
            ),
            "port": DictElement(
                parameter_form=Integer(
                    title=Title("Bazel Cache Port"),
                    help_text=Help(
                        "Use this option to query a port which is different from standard port 8080."
                    ),
                    custom_validate=[
                        NetworkPort(),
                    ],
                    prefill=DefaultValue(8080),
                ),
                required=False,
            ),
            "protocol": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Protocol"),
                    elements=[
                        SingleChoiceElement(name="http", title=Title("HTTP")),
                        SingleChoiceElement(name="https", title=Title("HTTPS")),
                    ],
                    prefill=DefaultValue("https"),
                ),
                required=True,
            ),
            "no_cert_check": DictElement(
                parameter_form=BooleanChoice(
                    label=Label("SSL certificate verification"),
                    prefill=DefaultValue(False),
                ),
                required=True,
            ),
        },
    )


rule_spec_bazel_cache = SpecialAgent(
    name="bazel_cache",
    title=Title("Bazel Remote Cache"),
    topic=Topic.APPLICATIONS,
    parameter_form=_formspec_bazel_cache,
)
