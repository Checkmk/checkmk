#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    MultipleChoice,
    MultipleChoiceElement,
    Password,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _formspec_netapp_ontap() -> Dictionary:
    return Dictionary(
        title=Title("NetApp via Ontap REST API"),
        help_text=Help(
            "This rule set selects the NetApp special agent instead of the normal Checkmk Agent "
            "and allows monitoring via the NetApp Ontap REST API."
        ),
        elements={
            "username": DictElement(
                parameter_form=String(
                    title=Title("Username"),
                    help_text=Help(
                        "The username that should be used for accessing the NetApp API."
                    ),
                    custom_validate=[
                        LengthInRange(min_value=1),
                    ],
                ),
                required=True,
            ),
            "password": DictElement(
                parameter_form=Password(
                    help_text=Help("The password of the user."),
                    title=Title("Password of the user"),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "no_cert_check": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Skip TLS certificate verification"),
                    prefill=DefaultValue(False),
                ),
                required=True,
            ),
            "skip_elements": DictElement(
                parameter_form=MultipleChoice(
                    title=Title("Performance improvements"),
                    help_text=Help(
                        "Here you can configure whether the performance counters should get queried. "
                        "This can save quite a lot of CPU load on larger systems."
                    ),
                    elements=[
                        MultipleChoiceElement(
                            name="ctr_volumes",
                            title=Title("Do not query volume performance counters"),
                        ),
                    ],
                ),
            ),
        },
    )


rule_spec_netapp_ontap = SpecialAgent(
    name="netapp_ontap",
    title=Title("NetApp via Ontap REST API"),
    topic=Topic.APPLICATIONS,
    parameter_form=_formspec_netapp_ontap,
)
