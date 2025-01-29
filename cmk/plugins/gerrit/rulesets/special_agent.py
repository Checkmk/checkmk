#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange, NetworkPort
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic

rule_spec_gerrit = SpecialAgent(
    name="gerrit",
    title=Title("Gerrit"),
    topic=Topic.APPLICATIONS,
    parameter_form=lambda: Dictionary(
        title=Title("Gerrit connection"),
        help_text=Help("Requests data from a Gerrit instance."),
        elements={
            "instance": DictElement(
                parameter_form=String(
                    title=Title("Gerrit instance to query."),
                    help_text=Help(
                        "Use this option to set which instance should be checked by the special "
                        "agent. Please add the host name here, e.g. my_gerrit.com."
                    ),
                    custom_validate=[LengthInRange(min_value=1)],
                    macro_support=True,
                ),
                required=True,
            ),
            "protocol": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Protocol"),
                    help_text=Help("Defaults to 'https' when not provided."),
                    elements=[
                        SingleChoiceElement(name="http", title=Title("HTTP")),
                        SingleChoiceElement(name="https", title=Title("HTTPS")),
                    ],
                    prefill=DefaultValue("https"),
                ),
            ),
            "port": DictElement(
                parameter_form=Integer(
                    title=Title("Port"),
                    help_text=Help("Use this option to query a non-standard port."),
                    prefill=DefaultValue(443),
                    custom_validate=[NetworkPort()],
                )
            ),
            "user": DictElement(
                parameter_form=String(
                    title=Title("Username"),
                    help_text=Help(
                        "The username that should be used for accessing the Gerrit API. "
                        "Must have (at least) read permissions."
                    ),
                    custom_validate=[LengthInRange(min_value=1)],
                ),
                required=True,
            ),
            "password": DictElement(
                parameter_form=Password(
                    title=Title("Password of the user"),
                    custom_validate=[LengthInRange(min_value=1)],
                ),
                required=True,
            ),
        },
    ),
)
