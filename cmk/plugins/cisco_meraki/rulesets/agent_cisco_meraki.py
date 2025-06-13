#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    List,
    migrate_to_password,
    migrate_to_proxy,
    MultipleChoice,
    MultipleChoiceElement,
    Password,
    Proxy,
    String,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _migrate_to_valid_ident(value: object) -> Sequence[str]:
    if not isinstance(value, Iterable):
        raise ValueError("Invalid value {value} for sections")

    name_mapping = {
        "licenses-overview": "licenses_overview",
        "device-statuses": "device_statuses",
        "sensor-readings": "sensor_readings",
    }

    return [name_mapping.get(s, s) for s in value if isinstance(s, str)]


def _form_special_agent_cisco_meraki() -> Dictionary:
    return Dictionary(
        title=Title("Cisco Meraki"),
        elements={
            "api_key": DictElement(
                parameter_form=Password(title=Title("API key"), migrate=migrate_to_password),
                required=True,
            ),
            "proxy": DictElement(parameter_form=Proxy(migrate=migrate_to_proxy)),
            "sections": DictElement(
                parameter_form=MultipleChoice(
                    title=Title("Sections"),
                    elements=[
                        MultipleChoiceElement(
                            name="licenses_overview", title=Title("Organization licenses overview")
                        ),
                        MultipleChoiceElement(
                            name="device_statuses", title=Title("Organization device statuses")
                        ),
                        MultipleChoiceElement(
                            name="sensor_readings", title=Title("Organization sensor readings")
                        ),
                    ],
                    migrate=_migrate_to_valid_ident,
                )
            ),
            "orgs": DictElement(
                parameter_form=List(
                    element_template=String(macro_support=True), title=Title("Organizations")
                )
            ),
        },
    )


rule_spec_cisco_meraki = SpecialAgent(
    name="cisco_meraki",
    title=Title("Cisco Meraki"),
    topic=Topic.APPLICATIONS,
    parameter_form=_form_special_agent_cisco_meraki,
)
